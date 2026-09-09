from datetime import timedelta
from django.utils.timezone import now
from asistencia.models import RegistroAsistencia, HorarioFuncionario, DiaFestivo, AnoEscolar
from permisos.models import SolicitudPermiso
from licencias.models import LicenciaMedica


def _reevaluar_medio_dia(registro, permisos_por_fecha, fecha):
    """
    Reevalúa al vuelo el estado de un registro real cuando tiene un permiso de medio día.
    Devuelve el estado corregido: AUSENTE, MEDIO_DIA, SIN_MARCACION_ENTRADA.
    """
    permiso = permisos_por_fecha.get(fecha)
    if not permiso or permiso.dias_solicitados != 0.5:
        return None
    entrada = registro.hora_entrada_real
    salida = registro.hora_salida_real
    if not entrada and not salida:
        return 'AUSENTE'
    if permiso.jornada == 'AM':
        if not entrada:
            return 'MEDIO_DIA'
        if not salida:
            return 'AUSENTE'
        return 'MEDIO_DIA'
    if permiso.jornada == 'PM':
        if not salida:
            return 'MEDIO_DIA'
        if not entrada:
            return 'SIN_MARCACION_ENTRADA'
        return 'MEDIO_DIA'
    return None


def _es_ausencia_real(registro, usuario=None, fecha=None):
    """
    Un registro se considera ausencia real (inasistencia) cuando:
    - el funcionario no marcó entrada NI salida (sin marcación alguna), y
    - NO tiene justificación manual.
    Es decir: solo cuentan como ausentes los días con entrada y salida sin marcación.
    """
    if getattr(registro, 'justificacion_manual', False):
        return False
    if not registro.hora_entrada_real and not registro.hora_salida_real:
        return True
    return False


def calcular_inasistencias_en_lote(usuarios, fecha_inicio_calc=None, fecha_fin_calc=None):
    """
    Calcula inasistencias reales en lote para una lista de usuarios en un rango de fechas.
    Optimizado para evitar el problema N+1: realiza consultas agrupadas y evaluaciones en memoria.
    Retorna un diccionario {usuario_id: total_inasistencias}.
    """
    if not usuarios:
        return {}

    # Filtrar solo usuarios con date_joined
    usuarios_validos = [u for u in usuarios if getattr(u, 'date_joined', None)]
    if not usuarios_validos:
        return {u.id: 0 for u in usuarios}

    # Determinar rango global para las consultas
    min_date_joined = min(u.date_joined.date() for u in usuarios_validos)
    inicio_global = max(fecha_inicio_calc or min_date_joined, min_date_joined)
    fin_global = min(fecha_fin_calc or now().date(), now().date())

    if inicio_global > fin_global:
        return {u.id: 0 for u in usuarios}

    # 1. Festivos en el rango global
    festivos = set(DiaFestivo.objects.filter(
        fecha__gte=inicio_global,
        fecha__lte=fin_global
    ).values_list('fecha', flat=True))

    # 2. Años escolares en el rango
    anos_escolares = {
        ae.ano: ae for ae in AnoEscolar.objects.filter(
            ano__gte=inicio_global.year,
            ano__lte=fin_global.year
        )
    }

    # 3. Horarios y días configurados
    horarios_qs = HorarioFuncionario.objects.filter(
        funcionario__in=usuarios_validos,
        activo=True
    ).prefetch_related('dias')

    horarios_map = {}
    dias_configurados_map = {}
    for h in horarios_qs:
        horarios_map[h.funcionario_id] = h
        dias_configurados_map[h.funcionario_id] = {
            (dh.dia_semana, dh.semana_tipo): dh
            for dh in h.dias.all() if dh.activo
        }

    # 4. Periodos de baja activos
    from users.models import BajaPeriodo
    bajas_qs = BajaPeriodo.objects.filter(
        usuario__in=usuarios_validos,
        estado='ACTIVO'
    )
    bajas_map = {u.id: [] for u in usuarios_validos}
    for bp in bajas_qs:
        bajas_map[bp.usuario_id].append(bp)

    # 5. Serenos y semanas asignadas
    serenos_ids = set(
        u.id for u in usuarios_validos
        if getattr(u, 'funcion', None) == 'SERENO' or getattr(u, 'tipo_funcionario', None) == 'SERENO'
    )
    semanas_map = {}
    if serenos_ids:
        from asistencia.models import SemanaAsignadaSereno
        semanas_qs = SemanaAsignadaSereno.objects.filter(
            funcionario_id__in=serenos_ids,
            anio__gte=inicio_global.year,
            anio__lte=fin_global.year
        )
        for sa in semanas_qs:
            semanas_map[(sa.funcionario_id, sa.anio, sa.semana_iso)] = sa.turno

    # 6. Permisos aprobados
    permisos_qs = SolicitudPermiso.objects.filter(
        usuario__in=usuarios_validos,
        estado='APROBADO',
        fecha_inicio__lte=fin_global,
        fecha_termino__gte=inicio_global
    )
    permisos_map = {u.id: {} for u in usuarios_validos}
    dias_permiso_map = {u.id: set() for u in usuarios_validos}
    for p in permisos_qs:
        d_p = max(p.fecha_inicio, inicio_global)
        p_fin = min(p.fecha_termino, fin_global)
        while d_p <= p_fin:
            dias_permiso_map[p.usuario_id].add(d_p)
            permisos_map[p.usuario_id][d_p] = p
            d_p += timedelta(days=1)

    # 7. Licencias médicas
    licencias_qs = LicenciaMedica.objects.filter(
        usuario__in=usuarios_validos,
        fecha_inicio__lte=fin_global
    )
    dias_licencia_map = {u.id: set() for u in usuarios_validos}
    for l in licencias_qs:
        fin_lic = l.fecha_inicio + timedelta(days=l.dias - 1)
        if fin_lic >= inicio_global:
            d_l = max(l.fecha_inicio, inicio_global)
            while d_l <= min(fin_lic, fin_global):
                dias_licencia_map[l.usuario_id].add(d_l)
                d_l += timedelta(days=1)

    # 8. Registros de asistencia
    registros_qs = RegistroAsistencia.objects.filter(
        funcionario__in=usuarios_validos,
        fecha__gte=inicio_global,
        fecha__lte=fin_global
    ).only('funcionario_id', 'fecha', 'hora_entrada_real', 'hora_salida_real', 'justificacion_manual', 'estado')

    registros_map = {u.id: {} for u in usuarios_validos}
    for r in registros_qs:
        registros_map[r.funcionario_id][r.fecha] = r

    # Función auxiliar para comprobar baja
    def esta_de_baja(usuario, dia, periodos):
        for bp in periodos:
            if bp.fecha_inicio <= dia:
                if bp.fecha_termino is None or dia <= bp.fecha_termino:
                    return True
        if usuario.is_on_leave or usuario.baja_date:
            if usuario.alta_date and dia >= usuario.alta_date:
                return False
            return usuario.baja_date is not None and dia >= usuario.baja_date
        return False

    # Evaluación en memoria día a día para cada usuario
    resultado = {}
    for usuario in usuarios:
        if not getattr(usuario, 'date_joined', None):
            resultado[usuario.id] = 0
            continue

        u_inicio = max(fecha_inicio_calc or usuario.date_joined.date(), usuario.date_joined.date())
        u_fin = min(fecha_fin_calc or now().date(), now().date())

        if u_inicio > u_fin:
            resultado[usuario.id] = 0
            continue

        es_sereno = usuario.id in serenos_ids
        horario = horarios_map.get(usuario.id)
        dias_configurados = dias_configurados_map.get(usuario.id, {})
        baja_periodos = bajas_map.get(usuario.id, [])
        dias_permiso = dias_permiso_map.get(usuario.id, set())
        permisos_por_fecha = permisos_map.get(usuario.id, {})
        dias_licencia = dias_licencia_map.get(usuario.id, set())
        registros_usuario = registros_map.get(usuario.id, {})

        inasistencias = 0
        d = u_inicio
        while d <= u_fin:
            # 1. Si está de baja, no es ausencia
            if esta_de_baja(usuario, d, baja_periodos):
                d += timedelta(days=1)
                continue

            # 2. Festivos y licencias siempre se excluyen
            if d in festivos or d in dias_licencia:
                d += timedelta(days=1)
                continue

            # 3. Permiso completo aprobado
            if d in dias_permiso:
                permiso = permisos_por_fecha.get(d)
                if permiso and permiso.dias_solicitados == 0.5:
                    pass  # Requiere evaluar marcación más abajo
                else:
                    d += timedelta(days=1)
                    continue

            # 4. Día con registro de asistencia
            if d in registros_usuario:
                registro = registros_usuario[d]
                if d in permisos_por_fecha:
                    permiso = permisos_por_fecha[d]
                    if permiso.dias_solicitados == 0.5:
                        estado_recalc = _reevaluar_medio_dia(registro, permisos_por_fecha, d)
                        if estado_recalc == 'AUSENTE' and not getattr(registro, 'justificacion_manual', False):
                            inasistencias += 1
                        d += timedelta(days=1)
                        continue

                if _es_ausencia_real(registro):
                    inasistencias += 1
                d += timedelta(days=1)
                continue

            # 5. Sin registro: evaluar si correspondía asistir según horario y calendario escolar
            ano_escolar = anos_escolares.get(d.year)
            en_ano_escolar = True
            if ano_escolar:
                en_ano_escolar = (ano_escolar.sem1_inicio <= d <= ano_escolar.sem1_fin) or (ano_escolar.sem2_inicio <= d <= ano_escolar.sem2_fin)

            if en_ano_escolar:
                dia_semana = d.weekday()
                es_laboral = False
                if horario:
                    if es_sereno:
                        iso_year, iso_week, _ = d.isocalendar()
                        semana_t = semanas_map.get((usuario.id, iso_year, iso_week))
                        if semana_t is None:
                            semana_t = 1 if iso_week % 2 != 0 else 2
                        es_laboral = (dia_semana, semana_t) in dias_configurados or (dia_semana, None) in dias_configurados
                    else:
                        es_laboral = (dia_semana, None) in dias_configurados
                else:
                    es_laboral = dia_semana < 5

                if es_laboral:
                    inasistencias += 1

            d += timedelta(days=1)

        resultado[usuario.id] = inasistencias

    return resultado


def calcular_inasistencias_reales(usuario, fecha_inicio_calc=None, fecha_fin_calc=None):
    """
    Función individual para calcular inasistencias reales de un único usuario.
    Delega a calcular_inasistencias_en_lote para máximo rendimiento y cero duplicación.
    """
    res = calcular_inasistencias_en_lote([usuario], fecha_inicio_calc, fecha_fin_calc)
    return res.get(usuario.id, 0)


def calcular_metricas_cla_en_lote(funcionarios, year, mes):
    """
    Calcula las métricas de asistencia laboral para el Informe CLA en lote (optimizado O(1) queries).
    Métricas calculadas por funcionario:
      - atrasos_minutos: Minutos totales de retraso acumulados.
      - atrasos_formato: Formato "Xh Ym".
      - inasistencias: Días laborales completos ausentes sin justificación (sin entrada ni salida).
      - sin_entrada: Días donde registró salida pero NO marcó entrada (y no tenía permiso AM ni justificación).
      - sin_salida: Días donde registró entrada pero NO marcó salida (y no tenía permiso PM ni justificación).
      - sin_ambas: Días laborales esperados donde NO marcó ni entrada ni salida.
    Reglas de exclusión:
      - NO cuenta cuando hay licencias médicas (LicenciaMedica).
      - NO cuenta cuando hay días administrativos completos aprobados (SolicitudPermiso).
      - Medio día administrativo AM: falta de entrada autorizada; falta de salida sí se evalúa.
      - Medio día administrativo PM: falta de salida autorizada; falta de entrada sí se evalúa.
      - NO cuenta días festivos, períodos de baja ni días fuera del año escolar / horario laboral.
      - NO cuenta marcaciones con justificación manual.
    Retorna:
      Lista de dicts con las métricas de los funcionarios que tienen al menos una anomalía:
      (total_atrasos >= 60 or inasistencias > 0 or sin_entrada > 0 or sin_salida > 0 or sin_ambas > 0)
    """
    import calendar as cal_module
    from datetime import date as date_cls
    from users.models import BajaPeriodo
    from asistencia.models import SemanaAsignadaSereno

    if not funcionarios:
        return []

    funcionarios_validos = [u for u in funcionarios if getattr(u, 'date_joined', None)]
    if not funcionarios_validos:
        return []

    today = now().date()
    primer_dia_mes = date_cls(int(year), int(mes), 1)
    ultimo_dia_mes = date_cls(int(year), int(mes), cal_module.monthrange(int(year), int(mes))[1])
    ultimo_dia = min(ultimo_dia_mes, today)

    if primer_dia_mes > today:
        return []

    # 1. Festivos del mes
    festivos = set(DiaFestivo.objects.filter(
        fecha__range=(primer_dia_mes, ultimo_dia_mes)
    ).values_list('fecha', flat=True))

    # 2. Año escolar
    ano_escolar = AnoEscolar.objects.filter(ano=int(year)).first()

    # 3. Horarios y días configurados
    horarios_qs = HorarioFuncionario.objects.filter(
        funcionario__in=funcionarios_validos,
        activo=True
    ).prefetch_related('dias')

    horarios_map = {}
    dias_configurados_map = {}
    for h in horarios_qs:
        horarios_map[h.funcionario_id] = h
        dias_configurados_map[h.funcionario_id] = {
            (dh.dia_semana, dh.semana_tipo): dh
            for dh in h.dias.all() if dh.activo
        }

    # 4. Períodos de baja
    bajas_qs = BajaPeriodo.objects.filter(
        usuario__in=funcionarios_validos,
        estado='ACTIVO'
    )
    bajas_map = {u.id: [] for u in funcionarios_validos}
    for bp in bajas_qs:
        bajas_map[bp.usuario_id].append(bp)

    # 5. Serenos y semanas asignadas
    serenos_ids = set(
        u.id for u in funcionarios_validos
        if getattr(u, 'funcion', None) == 'SERENO' or getattr(u, 'tipo_funcionario', None) == 'SERENO'
    )
    semanas_map = {}
    if serenos_ids:
        semanas_qs = SemanaAsignadaSereno.objects.filter(
            funcionario_id__in=serenos_ids,
            anio=int(year)
        )
        for sa in semanas_qs:
            semanas_map[(sa.funcionario_id, sa.anio, sa.semana_iso)] = sa.turno

    # 6. Días administrativos aprobados
    permisos_qs = SolicitudPermiso.objects.filter(
        usuario__in=funcionarios_validos,
        estado='APROBADO',
        fecha_inicio__lte=ultimo_dia_mes,
        fecha_termino__gte=primer_dia_mes
    )
    dias_permiso_completo_map = {u.id: set() for u in funcionarios_validos}
    permisos_medio_dia_map = {u.id: {} for u in funcionarios_validos}

    for p in permisos_qs:
        d_p = max(p.fecha_inicio, primer_dia_mes)
        p_fin = min(p.fecha_termino, ultimo_dia_mes)
        while d_p <= p_fin:
            if getattr(p, 'dias_solicitados', 1.0) == 0.5:
                permisos_medio_dia_map[p.usuario_id][d_p] = p
            else:
                dias_permiso_completo_map[p.usuario_id].add(d_p)
            d_p += timedelta(days=1)

    # 7. Licencias médicas (excluidas totalmente)
    licencias_qs = LicenciaMedica.objects.filter(
        usuario__in=funcionarios_validos,
        fecha_inicio__lte=ultimo_dia_mes
    )
    dias_licencia_map = {u.id: set() for u in funcionarios_validos}
    for l in licencias_qs:
        fin_lic = l.fecha_inicio + timedelta(days=l.dias - 1)
        if fin_lic >= primer_dia_mes:
            d_l = max(l.fecha_inicio, primer_dia_mes)
            while d_l <= min(fin_lic, ultimo_dia_mes):
                dias_licencia_map[l.usuario_id].add(d_l)
                d_l += timedelta(days=1)

    # 8. Registros de asistencia del mes
    registros_qs = RegistroAsistencia.objects.filter(
        funcionario__in=funcionarios_validos,
        fecha__range=(primer_dia_mes, ultimo_dia)
    ).only('funcionario_id', 'fecha', 'hora_entrada_real', 'hora_salida_real', 'justificacion_manual', 'estado', 'minutos_retraso')

    registros_map = {u.id: {} for u in funcionarios_validos}
    for r in registros_qs:
        registros_map[r.funcionario_id][r.fecha] = r

    # Función auxiliar para comprobar período de baja
    def esta_de_baja(usuario, dia, periodos):
        for bp in periodos:
            if bp.fecha_inicio <= dia:
                if bp.fecha_termino is None or dia <= bp.fecha_termino:
                    return True
        if usuario.is_on_leave or usuario.baja_date:
            if usuario.alta_date and dia >= usuario.alta_date:
                return False
            return usuario.baja_date is not None and dia >= usuario.baja_date
        return False

    # Evaluación en memoria día a día para cada funcionario
    funcionarios_data = []
    for func in funcionarios:
        if not getattr(func, 'date_joined', None):
            continue

        func_registros = registros_map.get(func.id, {})

        # Minutos de retraso acumulados
        total_atrasos = sum(
            r.minutos_retraso or 0 for r in func_registros.values()
            if r.estado == 'RETRASO' and not getattr(r, 'justificacion_manual', False)
        )

        dias_licencia = dias_licencia_map.get(func.id, set())
        dias_permiso_comp = dias_permiso_completo_map.get(func.id, set())
        permisos_md = permisos_medio_dia_map.get(func.id, {})
        baja_periodos = bajas_map.get(func.id, [])
        horario = horarios_map.get(func.id)
        dias_configurados = dias_configurados_map.get(func.id, {})
        es_sereno = func.id in serenos_ids

        sin_entrada = 0
        sin_salida = 0
        sin_ambas = 0

        d = primer_dia_mes
        while d <= ultimo_dia:
            # No estaba contratado aún
            if d < func.date_joined.date():
                d += timedelta(days=1)
                continue

            # Período de baja
            if esta_de_baja(func, d, baja_periodos):
                d += timedelta(days=1)
                continue

            # Festivo o Licencia médica: EXCLUIDOS
            if d in festivos or d in dias_licencia:
                d += timedelta(days=1)
                continue

            # Día administrativo completo: EXCLUIDO
            if d in dias_permiso_comp:
                d += timedelta(days=1)
                continue

            # Fuera de año escolar
            en_ano_escolar = True
            if ano_escolar:
                en_ano_escolar = (
                    (ano_escolar.sem1_inicio <= d <= ano_escolar.sem1_fin) or
                    (ano_escolar.sem2_inicio <= d <= ano_escolar.sem2_fin)
                )
            if not en_ano_escolar:
                d += timedelta(days=1)
                continue

            # Día laboral según horario
            dia_semana = d.weekday()
            es_laboral = False
            if horario:
                if es_sereno:
                    iso_year, iso_week, _ = d.isocalendar()
                    semana_t = semanas_map.get((func.id, iso_year, iso_week))
                    if semana_t is None:
                        semana_t = 1 if iso_week % 2 != 0 else 2
                    es_laboral = (dia_semana, semana_t) in dias_configurados or (dia_semana, None) in dias_configurados
                else:
                    es_laboral = (dia_semana, None) in dias_configurados
            else:
                es_laboral = dia_semana < 5

            if not es_laboral:
                d += timedelta(days=1)
                continue

            es_hoy = (d == today)
            registro = func_registros.get(d)
            p_md = permisos_md.get(d)

            if registro:
                if getattr(registro, 'justificacion_manual', False) or registro.estado == 'JUSTIFICADO':
                    d += timedelta(days=1)
                    continue

                tiene_entrada = bool(registro.hora_entrada_real)
                tiene_salida = bool(registro.hora_salida_real)

                if p_md:
                    # Medio día administrativo
                    if p_md.jornada == 'AM':
                        if not tiene_salida and not es_hoy:
                            sin_salida += 1
                    elif p_md.jornada == 'PM':
                        if not tiene_entrada:
                            sin_entrada += 1
                    else:
                        if not tiene_entrada and not tiene_salida and not es_hoy:
                            sin_ambas += 1
                        elif not tiene_entrada:
                            sin_entrada += 1
                        elif not tiene_salida and not es_hoy:
                            sin_salida += 1
                else:
                    # Jornada normal
                    if not tiene_entrada and not tiene_salida:
                        if not es_hoy:
                            sin_ambas += 1
                    elif not tiene_entrada and tiene_salida:
                        sin_entrada += 1
                    elif tiene_entrada and not tiene_salida:
                        if not es_hoy:
                            sin_salida += 1
            else:
                # Sin registro en BD para día laboral esperado
                if not es_hoy:
                    if p_md:
                        if p_md.jornada == 'AM':
                            sin_salida += 1
                        elif p_md.jornada == 'PM':
                            sin_entrada += 1
                        else:
                            sin_ambas += 1
                    else:
                        sin_ambas += 1

            d += timedelta(days=1)

        inasistencias = sin_ambas

        # Criterio de inclusión: presencia de atrasos significativos, inasistencias o cualquier omisión de marca
        if total_atrasos >= 60 or inasistencias > 0 or sin_entrada > 0 or sin_salida > 0 or sin_ambas > 0:
            hrs = total_atrasos // 60
            mins = total_atrasos % 60
            funcionarios_data.append({
                'funcionario': func,
                'atrasos_minutos': total_atrasos,
                'atrasos_formato': f"{hrs}h {mins}m",
                'inasistencias': inasistencias,
                'sin_entrada': sin_entrada,
                'sin_salida': sin_salida,
                'sin_ambas': sin_ambas,
            })

    return funcionarios_data


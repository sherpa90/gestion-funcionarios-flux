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
    - el estado es AUSENTE o SIN_MARCACION_ENTRADA, y
    - NO tiene justificación manual,
    O bien cuando el funcionario olvidó la salida (tiene entrada pero no salida)
    y NO tiene justificación manual. Esto cubre el caso típico: marcó entrada AM
    pero olvidó marcar salida, lo que implica que no completó la jornada.
    """
    if getattr(registro, 'justificacion_manual', False):
        return False
    if registro.estado in ('AUSENTE', 'SIN_MARCACION_ENTRADA'):
        return True
    # Olvido de salida: tiene entrada pero no salida → inasistencia
    if registro.hora_entrada_real and not registro.hora_salida_real:
        return True
    return False


def calcular_inasistencias_reales(usuario, fecha_inicio_calc=None, fecha_fin_calc=None):
    if not usuario.date_joined:
        return 0
        
    inicio = max(fecha_inicio_calc or usuario.date_joined.date(), usuario.date_joined.date())
    fin = min(fecha_fin_calc or now().date(), now().date())
    
    if inicio > fin:
        return 0
        
    es_sereno = (
        getattr(usuario, 'funcion', None) == 'SERENO' or
        getattr(usuario, 'tipo_funcionario', None) == 'SERENO'
    )
        
    # Obtener registros reales
    registros = RegistroAsistencia.objects.filter(
        funcionario=usuario,
        fecha__gte=inicio,
        fecha__lte=fin
    ).values_list('fecha', flat=True)
    registros_set = set(registros)
    
    # Festivos
    festivos = set(DiaFestivo.objects.filter(fecha__gte=inicio, fecha__lte=fin).values_list('fecha', flat=True))
    
    # Permisos
    permisos = SolicitudPermiso.objects.filter(
        usuario=usuario, estado='APROBADO',
        fecha_inicio__lte=fin, fecha_termino__gte=inicio
    )
    dias_permiso = set()
    permisos_por_fecha = {}
    for p in permisos:
        d_p = max(p.fecha_inicio, inicio)
        while d_p <= min(p.fecha_termino, fin):
            dias_permiso.add(d_p)
            permisos_por_fecha[d_p] = p
            d_p += timedelta(days=1)
            
    # Licencias
    licencias = LicenciaMedica.objects.filter(
        usuario=usuario,
        fecha_inicio__lte=fin
    )
    dias_licencia = set()
    for l in licencias:
        fin_lic = l.fecha_inicio + timedelta(days=l.dias - 1)
        if fin_lic >= inicio:
            d_l = max(l.fecha_inicio, inicio)
            while d_l <= min(fin_lic, fin):
                dias_licencia.add(d_l)
                d_l += timedelta(days=1)
                
    # Horario
    horario = HorarioFuncionario.objects.filter(funcionario=usuario, activo=True).first()
    
    # Pre-cargar configuraciones de DiaHorario
    dias_configurados = {}
    if horario:
        for dh in horario.dias.filter(activo=True):
            dias_configurados[(dh.dia_semana, dh.semana_tipo)] = dh
            
    # Pre-cargar asignaciones de semanas si es sereno
    semanas_asignadas_dict = {}
    if es_sereno:
        from asistencia.models import SemanaAsignadaSereno
        qs = SemanaAsignadaSereno.objects.filter(
            funcionario=usuario,
            anio__gte=inicio.year,
            anio__lte=fin.year
        )
        for sa in qs:
            semanas_asignadas_dict[(sa.anio, sa.semana_iso)] = sa.turno
        
    # Ano escolar cache
    ano_escolar_cache = {}
    def get_ano_escolar(year):
        if year not in ano_escolar_cache:
            ano_escolar_cache[year] = AnoEscolar.objects.filter(ano=year).first()
        return ano_escolar_cache[year]
    
    inasistencias = 0
    d = inicio
    while d <= fin:
        # Si el funcionario está de baja en este día, no es ausencia
        if usuario.is_on_baja_on_date(d):
            d += timedelta(days=1)
            continue

        # Festivos y licencias siempre se excluyen
        if d in festivos or d in dias_licencia:
            d += timedelta(days=1)
            continue

        # Si tiene permiso completo aprobado ese día, no es ausencia
        if d in dias_permiso:
            # Verificar si es medio día: el día sigue requiriendo evaluación
            permiso = permisos_por_fecha.get(d)
            if permiso and permiso.dias_solicitados == 0.5:
                pass  # cae a la lógica de evaluación más abajo
            else:
                d += timedelta(days=1)
                continue

        if d in registros_set:
            # Si tiene registro real AUSENTE/SIN_MARCACION sin justificación, contar como ausencia
            # (excepto si tiene medio día que cubre la jornada)
            if d in permisos_por_fecha:
                permiso = permisos_por_fecha[d]
                if permiso.dias_solicitados == 0.5:
                    # Reevaluar: si tras aplicar lógica de medio día sigue siendo AUSENTE, contar
                    try:
                        registro = RegistroAsistencia.objects.get(funcionario=usuario, fecha=d)
                    except RegistroAsistencia.DoesNotExist:
                        registro = None
                    if registro:
                        estado_recalc = _reevaluar_medio_dia(registro, permisos_por_fecha, d)
                        if estado_recalc == 'AUSENTE' and not getattr(registro, 'justificacion_manual', False):
                            inasistencias += 1
                    d += timedelta(days=1)
                    continue
            # Cualquier otro estado con registro: evaluar si es ausencia real
            try:
                registro = RegistroAsistencia.objects.get(funcionario=usuario, fecha=d)
            except RegistroAsistencia.DoesNotExist:
                registro = None
            if registro and _es_ausencia_real(registro):
                inasistencias += 1
            d += timedelta(days=1)
            continue

        # Sin registro: evaluar si es día laboral activo
        ano_escolar = get_ano_escolar(d.year)
        en_ano_escolar = True
        if ano_escolar:
            en_ano_escolar = (ano_escolar.sem1_inicio <= d <= ano_escolar.sem1_fin) or (ano_escolar.sem2_inicio <= d <= ano_escolar.sem2_fin)

        if en_ano_escolar:
            dia_semana = d.weekday()
            es_laboral = False
            if horario:
                if es_sereno:
                    iso_year, iso_week, _ = d.isocalendar()
                    semana_t = semanas_asignadas_dict.get((iso_year, iso_week))
                    if semana_t is None:
                        # Fallback a la paridad de la semana
                        semana_t = 1 if iso_week % 2 != 0 else 2

                    # Buscar dia_semana con semana_tipo=semana_t o semana_tipo=None
                    es_laboral = (dia_semana, semana_t) in dias_configurados or (dia_semana, None) in dias_configurados
                else:
                    # Usuario regular
                    es_laboral = (dia_semana, None) in dias_configurados
            else:
                # Fallback si no tiene horario
                es_laboral = dia_semana < 5

            if es_laboral:
                inasistencias += 1

        d += timedelta(days=1)
        
    return inasistencias

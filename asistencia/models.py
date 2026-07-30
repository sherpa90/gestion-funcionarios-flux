from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError


class HorarioFuncionario(models.Model):
    """Horario de entrada asignado a cada funcionario"""
    funcionario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="horario"
    )
    hora_entrada = models.TimeField(
        help_text="Hora de entrada asignada (ej: 08:00:00)"
    )

    activo = models.BooleanField(
        default=True,
        help_text="Si el horario está activo"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Horario de Funcionario"
        verbose_name_plural = "Horarios de Funcionarios"
        ordering = ["funcionario__last_name", "funcionario__first_name"]

    def __str__(self):
        return f"{self.funcionario.get_full_name()} - {self.hora_entrada}"


class DiaHorario(models.Model):
    """Configuración de horario por día de la semana para un funcionario"""
    DIA_CHOICES = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]

    horario = models.ForeignKey(
        HorarioFuncionario,
        on_delete=models.CASCADE,
        related_name='dias'
    )
    dia_semana = models.IntegerField(choices=DIA_CHOICES)
    hora_entrada = models.TimeField(
        null=True, 
        blank=True,
        help_text="Hora de entrada para este día"
    )
    hora_salida = models.TimeField(
        null=True, 
        blank=True,
        help_text="Hora de salida para este día"
    )
    activo = models.BooleanField(
        default=True,
        help_text="Indica si el funcionario debe trabajar este día"
    )
    semana_tipo = models.IntegerField(
        choices=[(1, 'Semana 1'), (2, 'Semana 2')],
        null=True,
        blank=True,
        help_text="Para horarios rotativos (Semana 1/2). Si es nulo, aplica a todas las semanas."
    )

    class Meta:
        verbose_name = "Día de Horario"
        verbose_name_plural = "Días de Horario"
        ordering = ['dia_semana']
        unique_together = ['horario', 'dia_semana', 'semana_tipo']

    def __str__(self):
        sem = f" (S{self.semana_tipo})" if self.semana_tipo else ""
        return f"{self.horario.funcionario.get_full_name()} - {self.get_dia_semana_display()}{sem}"

    @staticmethod
    def get_semana_tipo(fecha, funcionario=None):
        """
        Retorna la paridad de la semana (1 para impares, 2 para pares)
        según el estándar ISO, o la asignación personalizada para serenos.
        """
        if not fecha:
            return 1
            
        if funcionario:
            es_sereno = (
                getattr(funcionario, 'funcion', None) == 'SERENO' or
                getattr(funcionario, 'tipo_funcionario', None) == 'SERENO'
            )
            if es_sereno:
                iso_year, iso_week, _ = fecha.isocalendar()
                asignacion = SemanaAsignadaSereno.objects.filter(
                    funcionario=funcionario,
                    anio=iso_year,
                    semana_iso=iso_week
                ).first()
                if asignacion:
                    return asignacion.turno

        num_semana = fecha.isocalendar()[1]
        return 1 if num_semana % 2 != 0 else 2


class DiaFestivo(models.Model):
    """Días festivos que no cuentan para asistencia"""
    fecha = models.DateField(unique=True, help_text="Fecha del día festivo")
    nombre = models.CharField(max_length=100, help_text="Nombre del día festivo")
    descripcion = models.TextField(blank=True, help_text="Descripción opcional")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="dias_festivos_creados"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Día Festivo"
        verbose_name_plural = "Días Festivos"
        ordering = ["fecha"]

    def __str__(self):
        return f"{self.fecha} - {self.nombre}"

    def clean(self):
        pass

    @staticmethod
    def es_dia_festivo(fecha):
        """Verifica si una fecha es día festivo"""
        return DiaFestivo.objects.filter(fecha=fecha).exists()


class HorarioExcepcional(models.Model):
    """Horario global que aplica excepcionalmente a todos los funcionarios para una fecha específica"""
    fecha = models.DateField(unique=True, help_text="Fecha a la que aplica este horario excepcional")
    hora_entrada = models.TimeField(null=True, blank=True, help_text="Hora de entrada obligatoria (dejar en blanco si no aplica entrada)")
    hora_salida = models.TimeField(null=True, blank=True, help_text="Hora de salida autorizada (dejar en blanco si no aplica salida)")
    motivo = models.CharField(max_length=255, help_text="Motivo de este horario excepcional (ej: Día del Profesor, Corte de agua)")
    APLICA_A_CHOICES = [
        ('TODOS', 'Todos los funcionarios'),
        ('FUNCIONARIOS', 'Solo funcionarios (no serenos)'),
        ('SERENOS', 'Solo serenos'),
    ]
    aplica_a = models.CharField(
        max_length=20,
        choices=APLICA_A_CHOICES,
        default='TODOS',
        help_text="Grupo de funcionarios al que aplica este horario excepcional"
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="horarios_excepcionales_creados"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Horario Excepcional"
        verbose_name_plural = "Horarios Excepcionales"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.fecha} - {self.motivo}"

    def aplica_a_funcionario(self, funcionario):
        """Verifica si este horario excepcional aplica a un funcionario dado"""
        if self.aplica_a == 'TODOS':
            return True
        es_sereno = (
            getattr(funcionario, 'funcion', None) == 'SERENO' or
            getattr(funcionario, 'tipo_funcionario', None) == 'SERENO'
        )
        if self.aplica_a == 'SERENOS':
            return es_sereno
        if self.aplica_a == 'FUNCIONARIOS':
            return not es_sereno
        return True

    def aplica_a_funcionario_id(self, funcionario_id):
        """Versión optimizada que verifica si aplica a un funcionario por ID sin cargar el objeto completo"""
        if self.aplica_a == 'TODOS':
            return True
        try:
            from users.models import CustomUser
            user = CustomUser.objects.filter(pk=funcionario_id).first()
            if not user:
                return False
            es_sereno = (
                getattr(user, 'funcion', None) == 'SERENO' or
                getattr(user, 'tipo_funcionario', None) == 'SERENO'
            )
            if self.aplica_a == 'SERENOS':
                return es_sereno
            if self.aplica_a == 'FUNCIONARIOS':
                return not es_sereno
            return True
        except Exception:
            return False


class AlegacionAsistencia(models.Model):
    """Alegaciones de usuarios sobre sus registros de asistencia"""

    ESTADO_CHOICES = [
        ("PENDIENTE", "Pendiente de Revisión"),
        ("APROBADA", "Aprobada"),
        ("RECHAZADA", "Rechazada"),
    ]

    registro_asistencia = models.OneToOneField(
        'RegistroAsistencia',
        on_delete=models.CASCADE,
        related_name="alegacion"
    )
    motivo = models.TextField(help_text="Motivo de la alegación")
    evidencia = models.FileField(
        upload_to='alegaciones/',
        blank=True,
        null=True,
        help_text="Archivo de evidencia opcional"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="PENDIENTE"
    )
    respuesta_admin = models.TextField(
        blank=True,
        help_text="Respuesta del administrador"
    )
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alegaciones_revisadas"
    )
    fecha_alegacion = models.DateTimeField(auto_now_add=True)
    fecha_revision = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Alegación de Asistencia"
        verbose_name_plural = "Alegaciones de Asistencia"
        ordering = ["-fecha_alegacion"]

    def __str__(self):
        return f"Alegación {self.registro_asistencia} - {self.estado}"

    def puede_revisar(self, user):
        """Verifica si un usuario puede revisar esta alegación"""
        return user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']


class RegistroAsistencia(models.Model):
    """Registro diario de asistencia de un funcionario"""

    ESTADO_CHOICES = [
        ("PUNTUAL", "Puntual"),
        ("RETRASO", "Retraso"),
        ("AUSENTE", "Ausente"),
        ("JUSTIFICADO", "Justificado"),
        ("SIN_MARCACION_ENTRADA", "Sin Marcación de Entrada"),
        ("MEDIO_DIA", "Medio Día Administrativo"),
        ("DIA_ADMINISTRATIVO", "Día Administrativo"),
        ("LICENCIA_MEDICA", "Licencia Médica"),
        ("BAJA", "Baja"),
        ("DIA_FESTIVO", "Día Festivo"),
        ("SIN_HORARIO", "Sin Horario Asignado"),
        ("SIN_DATA", "Sin Datos"),
    ]

    funcionario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="registros_asistencia"
    )
    fecha = models.DateField()
    hora_entrada_real = models.TimeField(
        null=True,
        blank=True,
        help_text="Hora de entrada registrada por el reloj control"
    )
    hora_salida_real = models.TimeField(
        null=True,
        blank=True,
        help_text="Hora de salida registrada por el reloj control"
    )
    minutos_retraso = models.IntegerField(
        default=0,
        help_text="Minutos de retraso calculados"
    )
    minutos_trabajados = models.IntegerField(
        null=True,
        blank=True,
        help_text="Minutos totales trabajados (calculado automáticamente)"
    )
    estado = models.CharField(
        max_length=25,
        choices=ESTADO_CHOICES,
        default="AUSENTE"
    )
    horario_asignado = models.ForeignKey(
        HorarioFuncionario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Horario que tenía asignado en esa fecha"
    )
    procesado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_procesados"
    )
    fecha_procesamiento = models.DateTimeField(
        auto_now_add=True
    )
    justificacion_manual = models.TextField(
        blank=True,
        help_text="Justificación manual agregada por administrador"
    )
    justificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_justificados"
    )
    fecha_justificacion = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Registro de Asistencia"
        verbose_name_plural = "Registros de Asistencia"
        ordering = ["-fecha", "funcionario__last_name"]
        unique_together = ["funcionario", "fecha"]

    def __str__(self):
        return f"{self.funcionario.get_full_name()} - {self.fecha} - {self.get_estado_display()}"

    @property
    def horario_dia(self):
        """Retorna la configuración de horario para el día específico de este registro (considerando excepciones y semana_tipo para serenos)"""
        dia_semana = self.fecha.weekday()
        semana_t = DiaHorario.get_semana_tipo(self.fecha, self.funcionario)

        # PRIORIDAD: Si hay edición manual justificada, usar horario regular (ignorar excepcional)
        if self.justificado_por:
            if not self.horario_asignado:
                return None
            dia_horario = self.horario_asignado.dias.filter(dia_semana=dia_semana, semana_tipo=semana_t).first()
            if not dia_horario:
                dia_horario = self.horario_asignado.dias.filter(dia_semana=dia_semana, semana_tipo__isnull=True).first()
            return dia_horario

        # Si no hay justificación manual, verificar horario excepcional
        excepcional = HorarioExcepcional.objects.filter(fecha=self.fecha).first()
        if excepcional and excepcional.aplica_a_funcionario(self.funcionario):
            class VirtualHorario:
                def __init__(self, ex):
                    self.hora_entrada = ex.hora_entrada
                    self.hora_salida = ex.hora_salida
            return VirtualHorario(excepcional)

        if not self.horario_asignado:
            return None

        dia_horario = self.horario_asignado.dias.filter(dia_semana=dia_semana, semana_tipo=semana_t).first()
        if not dia_horario:
            dia_horario = self.horario_asignado.dias.filter(dia_semana=dia_semana, semana_tipo__isnull=True).first()

        return dia_horario

    def calcular_retraso(self):
        """Calcula los minutos de retraso basado en el horario asignado o excepcional"""
        if not self.hora_entrada_real:
            return 0



        # dia_semana siempre definido antes de cualquier bifurcación
        dia_semana = self.fecha.weekday()

        # PRIORIDAD: Si hay edición manual justificada, usar horario regular (ignorar excepcional)
        if self.justificado_por:
            if not self.horario_asignado:
                return 0
            dia_horario = self.horario_asignado.dias.filter(dia_semana=dia_semana).first()

            if dia_horario:
                if not dia_horario.activo or not dia_horario.hora_entrada:
                    return 0
                hora_esperada = dia_horario.hora_entrada
            else:
                hora_esperada = self.horario_asignado.hora_entrada
        else:
            # Verificar horario excepcional
            excepcional = HorarioExcepcional.objects.filter(fecha=self.fecha).first()
            if excepcional and excepcional.aplica_a_funcionario(self.funcionario):
                if not excepcional.hora_entrada:
                    return 0
                hora_esperada = excepcional.hora_entrada
            else:
                if not self.horario_asignado:
                    return 0
                # Obtener tipo de semana
                semana_t = DiaHorario.get_semana_tipo(self.fecha, self.funcionario)
                # Primero buscar específico para esta semana, si no el universal
                dia_horario = self.horario_asignado.dias.filter(dia_semana=dia_semana, semana_tipo=semana_t).first()
                if not dia_horario:
                    dia_horario = self.horario_asignado.dias.filter(dia_semana=dia_semana, semana_tipo=None).first()

                if dia_horario:
                    if not dia_horario.activo or not dia_horario.hora_entrada:
                        return 0
                    hora_esperada = dia_horario.hora_entrada
                else:
                    hora_esperada = getattr(self.horario_asignado, 'hora_entrada', None)
                    if not hora_esperada:
                        return 0

        minutos_asignados = hora_esperada.hour * 60 + hora_esperada.minute
        minutos_reales = self.hora_entrada_real.hour * 60 + self.hora_entrada_real.minute

        diferencia = minutos_reales - minutos_asignados
        tolerancia = 0

        if diferencia <= tolerancia:
            return 0

        return max(0, diferencia)

    def calcular_tiempo_trabajado(self):
        """Calcula los minutos trabajados basado en entrada y salida"""
        if not self.hora_entrada_real or not self.hora_salida_real:
            return None

        # Crear objetos datetime para comparación
        entrada = timezone.datetime.combine(self.fecha, self.hora_entrada_real)
        salida = timezone.datetime.combine(self.fecha, self.hora_salida_real)

        # Si la salida es anterior a la entrada (turno nocturno de serenos PM->AM)
        # la salida corresponde al día siguiente
        if salida <= entrada:
            salida = salida + timedelta(days=1)

        # Calcular diferencia en minutos
        diferencia = (salida - entrada).total_seconds() / 60
        return max(0, int(diferencia))

    def tiene_permiso_aprobado(self):
        """Verifica si el funcionario tiene un permiso administrativo aprobado para esta fecha"""
        try:
            from permisos.models import SolicitudPermiso
            # Verificar si hay un permiso aprobado que cubra esta fecha
            permisos_aprobados = SolicitudPermiso.objects.filter(
                usuario=self.funcionario,
                estado='APROBADO',
                fecha_inicio__lte=self.fecha,
                fecha_termino__gte=self.fecha
            )
            return permisos_aprobados.exists()
        except ImportError:
            # Si no existe el modelo de permisos, retornar False
            return False

    def tiene_permiso_aprobado_jornada(self, jornada_check=None):
        """Verifica si el funcionario tiene un permiso administrativo aprobado para esta fecha y jornada específica"""
        try:
            from permisos.models import SolicitudPermiso
            # Verificar si hay un permiso aprobado que cubra esta fecha
            permisos_aprobados = SolicitudPermiso.objects.filter(
                usuario=self.funcionario,
                estado='APROBADO',
                fecha_inicio__lte=self.fecha,
                fecha_termino__gte=self.fecha
            )

            if not jornada_check:
                # Si no especificamos jornada, cualquier permiso aprobado sirve
                return permisos_aprobados.exists()

            # Para medio día, verificar que la jornada coincida
            for permiso in permisos_aprobados:
                if permiso.dias_solicitados == 0.5:
                    # Para medio día, la jornada debe coincidir
                    if permiso.jornada == jornada_check:
                        return True
                else:
                    # Para día completo, cualquier jornada está cubierta
                    return True

            return False
        except ImportError:
            # Si no existe el modelo de permisos, retornar False
            return False

    def tiene_licencia_medica(self):
        """Verifica si el funcionario tiene una licencia médica que cubra esta fecha"""
        try:
            from licencias.models import LicenciaMedica
            # Verificar si hay una licencia médica que cubra esta fecha
            licencias = LicenciaMedica.objects.filter(
                usuario=self.funcionario,
                fecha_inicio__lte=self.fecha,
                fecha_inicio__gte=self.fecha - timedelta(days=30)  # Considerar hasta 30 días antes
            )

            for licencia in licencias:
                fecha_fin = licencia.fecha_inicio + timedelta(days=licencia.dias - 1)
                if self.fecha <= fecha_fin:
                    return True

            return False
        except ImportError:
            # Si no existe el modelo de licencias, retornar False
            return False

    def obtener_tipo_licencia_o_permiso(self):
        """Retorna el tipo específico de licencia médica o permiso que cubre esta fecha"""
        try:
            from licencias.models import LicenciaMedica
            from permisos.models import SolicitudPermiso

            # Primero buscar en licencias médicas
            licencias = LicenciaMedica.objects.filter(
                usuario=self.funcionario,
                fecha_inicio__lte=self.fecha,
                fecha_inicio__gte=self.fecha - timedelta(days=60)
            )

            for licencia in licencias:
                fecha_fin = licencia.fecha_inicio + timedelta(days=licencia.dias - 1)
                if self.fecha >= licencia.fecha_inicio and self.fecha <= fecha_fin:
                    return licencia.get_tipo_display()

            # Si no hay licencia médica, buscar permisos aprobados que podrían ser "permisos sin goce"
            permisos = SolicitudPermiso.objects.filter(
                usuario=self.funcionario,
                estado='APROBADO',
                fecha_inicio__lte=self.fecha,
                fecha_termino__gte=self.fecha
            )

            if permisos.exists():
                # Si hay permisos aprobados en esta fecha, asumimos que es "Permiso sin Goce de Remuneraciones"
                return "Permiso sin Goce de Remuneraciones"

            return None
        except ImportError:
            return None

    @property
    def horario_excepcional(self):
        """Retorna el horario excepcional para esta fecha si existe y aplica a este funcionario"""
        try:
            from .models import HorarioExcepcional
            excepcional = HorarioExcepcional.objects.filter(fecha=self.fecha).first()
            if excepcional and excepcional.aplica_a_funcionario(self.funcionario):
                return excepcional
            return None
        except Exception:
            return None

            return None
        except ImportError:
            return None

    @property
    def permiso_detalle(self):
        """Retorna detalles del permiso si existe para esta fecha"""
        try:
            from permisos.models import SolicitudPermiso
            permiso = SolicitudPermiso.objects.filter(
                usuario=self.funcionario,
                estado='APROBADO',
                fecha_inicio__lte=self.fecha,
                fecha_termino__gte=self.fecha
            ).first()
            if permiso:
                return {
                    'es_medio_dia': permiso.dias_solicitados == 0.5,
                    'jornada': permiso.jornada if permiso.dias_solicitados == 0.5 else None,
                    'jornada_display': permiso.get_jornada_display() if permiso.dias_solicitados == 0.5 else 'Día completo',
                    'dias': permiso.dias_solicitados,
                }
            return None
        except Exception:
            return None

    def determinar_estado(self):
        """Determina el estado basado en la hora de llegada, horario y permisos"""
        # Resetear retraso por defecto para recalcularlo en cada guardado
        self.minutos_retraso = 0

        if not self.horario_asignado:
            return "SIN_HORARIO"



        # Verificar si es día festivo (prioridad máxima)
        if DiaFestivo.es_dia_festivo(self.fecha):
            return "DIA_FESTIVO"

        # Verificar primero licencia médica (prioridad alta)
        if self.tiene_licencia_medica():
            return "LICENCIA_MEDICA"

        # Verificar permiso administrativo aprobado
        from permisos.models import SolicitudPermiso
        permisos_dia = SolicitudPermiso.objects.filter(
            usuario=self.funcionario,
            estado='APROBADO',
            fecha_inicio__lte=self.fecha,
            fecha_termino__gte=self.fecha
        )

        if permisos_dia.exists():
            # Verificar si es medio día o día completo
            for permiso in permisos_dia:
                if permiso.dias_solicitados == 0.5:
                    # Es medio día administrativo
                    # Solo cuenta retraso si marcó en la jornada que SÍ trabaja
                    if permiso.jornada == 'AM':
                        # Tiene libre en la mañana, trabaja en la tarde
                        # Sin marcación de salida → ausente en la jornada laboral (tarde)
                        # El medio día AM administrativo sigue vigente (accessible via permiso_detalle)
                        if not self.hora_salida_real:
                            return "JUSTIFICADO" if self.justificacion_manual else "AUSENTE"
                        if self.hora_entrada_real:
                            # Si marcó entrada, verificar si fue en la tarde (después de 12:00)
                            if self.hora_entrada_real.hour >= 12:
                                # Marcó en su jornada laboral (tarde) - verificar si fue puntual respecto a las 14:00
                                minutos_reales = self.hora_entrada_real.hour * 60 + self.hora_entrada_real.minute
                                # Hora de referencia para la tarde: 14:00 (2 PM)
                                minutos_referencia = 14 * 60
                                diferencia = minutos_reales - minutos_referencia
                                if diferencia > 0:
                                    self.minutos_retraso = max(0, diferencia)
                                return "MEDIO_DIA"
                            else:
                                # Marcó en la mañana pero tiene permiso AM - no debería contar retraso
                                return "MEDIO_DIA"
                        else:
                            # Tiene salida pero no entrada → sin marcación de entrada
                            return "JUSTIFICADO" if self.justificacion_manual else "SIN_MARCACION_ENTRADA"

                    elif permiso.jornada == 'PM':
                        # Tiene libre en la tarde, trabaja en la mañana
                        # Sin marcación de salida → ausente en la jornada laboral (mañana)
                        # El medio día PM administrativo sigue vigente (accessible via permiso_detalle)
                        if not self.hora_salida_real:
                            return "JUSTIFICADO" if self.justificacion_manual else "AUSENTE"
                        if self.hora_entrada_real:
                            # Verificar retraso solo respecto a la mañana
                            retraso = self.calcular_retraso()
                            self.minutos_retraso = retraso
                            return "MEDIO_DIA"
                        else:
                            # Tiene salida pero no entrada → sin marcación de entrada
                            return "JUSTIFICADO" if self.justificacion_manual else "SIN_MARCACION_ENTRADA"
                else:
                    # Día completo administrativo
                    return "DIA_ADMINISTRATIVO"

        # Determinar si es un día laboral activo base en su horario semanal
        dia_semana = self.fecha.weekday()
        semana_t = DiaHorario.get_semana_tipo(self.fecha, self.funcionario)
        
        # Buscar primero horario específico para esta semana (1 o 2)
        # Si no existe, cae al horario universal (semana_tipo=None)
        dia_horario = self.horario_asignado.dias.filter(
            dia_semana=dia_semana, 
            semana_tipo=semana_t
        ).first()
        
        if not dia_horario:
            dia_horario = self.horario_asignado.dias.filter(
                dia_semana=dia_semana, 
                semana_tipo__isnull=True
            ).first()
        
        if dia_horario:
            es_dia_activo_base = dia_horario.activo
        else:
            # Fallback lógico si no tiene configurado el DiaHorario
            es_sereno = self.funcionario.funcion == 'SERENO'
            es_dia_activo_base = True if es_sereno else dia_semana < 5

        # Verificar si hay horario excepcional
        excepcional = HorarioExcepcional.objects.filter(fecha=self.fecha).first()
        if excepcional and excepcional.aplica_a_funcionario(self.funcionario):
            # Un horario excepcional global solo aplica si el usuario ya trabajaba ese día
            tiene_horas = True if excepcional.hora_entrada or excepcional.hora_salida else False
            es_dia_activo = tiene_horas and es_dia_activo_base
        else:
            es_dia_activo = es_dia_activo_base

        if not es_dia_activo and not self.hora_entrada_real:
            return "DIA_LIBRE"

        # Calcular retraso base si hay marcación de entrada para que se mantenga actualizado
        # incluso si el registro está justificado manualmente
        if self.hora_entrada_real:
            self.minutos_retraso = self.calcular_retraso()

        # Verificar justificación manual
        if self.justificacion_manual:
            self.minutos_retraso = 0  # Resetear retraso cuando hay justificación
            return "JUSTIFICADO"

        if not self.hora_entrada_real:
            if self.hora_salida_real:
                # Hay marcación de salida pero no de entrada - no es ausencia
                return "SIN_MARCACION_ENTRADA"
            
            # Si no hay marcación y es anterior a su fecha de ingreso, no es ausente
            if self.fecha < self.funcionario.date_joined.date():
                return "SIN_DATA"
                
            return "AUSENTE"

        if self.minutos_retraso == 0:
            return "PUNTUAL"
        else:
            return "RETRASO"

    def save(self, *args, **kwargs):
        # Asignar horario actual activo del funcionario
        try:
            horario_actual = HorarioFuncionario.objects.filter(
                funcionario=self.funcionario, activo=True
            ).first()
            if horario_actual:
                self.horario_asignado = horario_actual
        except:
            # Si hay error, continuar sin asignar horario
            pass

        # Calcular tiempo trabajado si hay entrada y salida
        self.minutos_trabajados = self.calcular_tiempo_trabajado()

        # Determinar estado antes de guardar
        self.estado = self.determinar_estado()

        super().save(*args, **kwargs)


class AnoEscolar(models.Model):
    """Configuración del año escolar con 2 semestres"""
    ano = models.PositiveIntegerField(
        unique=True,
        help_text="Año escolar (ej: 2026)"
    )
    sem1_inicio = models.DateField(
        help_text="Fecha de inicio del primer semestre"
    )
    sem1_fin = models.DateField(
        help_text="Fecha de fin del primer semestre"
    )
    sem2_inicio = models.DateField(
        help_text="Fecha de inicio del segundo semestre"
    )
    sem2_fin = models.DateField(
        help_text="Fecha de fin del segundo semestre"
    )
    activo = models.BooleanField(
        default=False,
        help_text="Si este es el año escolar activo"
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="anos_escolares_creados"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Año Escolar"
        verbose_name_plural = "Años Escolares"
        ordering = ["-ano"]

    def __str__(self):
        return f"Año Escolar {self.ano}"

    @classmethod
    def get_activo(cls):
        """Retorna el año escolar activo o None"""
        return cls.objects.filter(activo=True).first()

    @classmethod
    def es_dia_escolar(cls, fecha):
        """Verifica si una fecha cae dentro de algún semestre del año escolar activo"""
        activo = cls.get_activo()
        if not activo:
            return True  # Si no hay año escolar configurado, asumir que es día escolar
        en_sem1 = activo.sem1_inicio <= fecha <= activo.sem1_fin
        en_sem2 = activo.sem2_inicio <= fecha <= activo.sem2_fin
        return en_sem1 or en_sem2

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.sem1_fin <= self.sem1_inicio:
            raise ValidationError("La fecha de fin del primer semestre debe ser posterior a la de inicio.")
        if self.sem2_fin <= self.sem2_inicio:
            raise ValidationError("La fecha de fin del segundo semestre debe ser posterior a la de inicio.")
        if self.sem2_inicio <= self.sem1_fin:
            raise ValidationError("El segundo semestre debe comenzar después de que termine el primero.")


class SemanaAsignadaSereno(models.Model):
    """Asignación de turno semanal para funcionarios serenos"""
    funcionario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='semanas_asignadas',
        help_text="Funcionario sereno al que se asigna la semana"
    )
    anio = models.IntegerField(help_text="Año de la semana asignada")
    semana_iso = models.IntegerField(help_text="Número de semana ISO (1-53)")
    turno = models.IntegerField(
        choices=[(1, 'Semana 1 (Impar)'), (2, 'Semana 2 (Par)')],
        help_text="Turno asignado para esa semana"
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True, help_text="Notas adicionales sobre la asignación")
    asignado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='semanas_asignadas_creadas'
    )

    class Meta:
        verbose_name = "Semana Asignada a Sereno"
        verbose_name_plural = "Semanas Asignadas a Serenos"
        ordering = ['funcionario__last_name', 'anio', 'semana_iso']
        unique_together = ['funcionario', 'anio', 'semana_iso']

    def __str__(self):
        return f"{self.funcionario.get_full_name()} - Año {self.anio}, Sem. {self.semana_iso}: Turno {self.turno}"

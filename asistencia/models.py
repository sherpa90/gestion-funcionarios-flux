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
    tolerancia_minutos = models.PositiveIntegerField(
        default=15,
        help_text="Minutos de tolerancia para considerar puntual"
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
        help_text="Hora de salida esperada para este día"
    )
    activo = models.BooleanField(
        default=True,
        help_text="Indica si el funcionario debe trabajar este día"
    )

    class Meta:
        verbose_name = "Día de Horario"
        verbose_name_plural = "Días de Horario"
        ordering = ['dia_semana']
        unique_together = ['horario', 'dia_semana']

    def __str__(self):
        return f"{self.horario.funcionario.get_full_name()} - {self.get_dia_semana_display()}"


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
        ("DIA_FESTIVO", "Día Festivo"),
        ("DIA_LIBRE", "Día Libre"),
        ("SIN_HORARIO", "Sin Horario Asignado"),
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
        """Retorna la configuración de horario para el día específico de este registro (considerando excepciones)"""
        # Verificar primero si hay un horario excepcional
        excepcional = HorarioExcepcional.objects.filter(fecha=self.fecha).first()
        if excepcional:
            class VirtualHorario:
                def __init__(self, ex):
                    self.hora_entrada = ex.hora_entrada
                    self.hora_salida = ex.hora_salida
            return VirtualHorario(excepcional)

        if not self.horario_asignado:
            return None
        
        # En Python, weekday() retorna 0 para Lunes y 6 para Domingo
        dia_semana = self.fecha.weekday()
        
        try:
            return self.horario_asignado.dias.get(dia_semana=dia_semana)
        except Exception:
            return None

    def calcular_retraso(self):
        """Calcula los minutos de retraso basado en el horario asignado o excepcional"""
        if not self.hora_entrada_real:
            return 0

        # Verificar primero horario excepcional
        excepcional = HorarioExcepcional.objects.filter(fecha=self.fecha).first()
        if excepcional:
            if not excepcional.hora_entrada:
                return 0 # Si el excepcional no exige hora de entrada, no hay retraso
            hora_esperada = excepcional.hora_entrada
        else:
            if not self.horario_asignado:
                return 0
            # Intentar obtener el horario específico para el día de la semana
            dia_semana = self.fecha.weekday()
            dia_horario = self.horario_asignado.dias.filter(dia_semana=dia_semana).first()

            if dia_horario:
                if not dia_horario.activo or not dia_horario.hora_entrada:
                    return 0 # No debería tener retraso en un día libre o sin hora configurada
                hora_esperada = dia_horario.hora_entrada
            else:
                # Fallback al horario general
                hora_esperada = self.horario_asignado.hora_entrada

        minutos_asignados = hora_esperada.hour * 60 + hora_esperada.minute

        minutos_reales = (self.hora_entrada_real.hour * 60 +
                         self.hora_entrada_real.minute)

        # Calcular diferencia en minutos
        diferencia = minutos_reales - minutos_asignados

        # Tolerancia (usar la del horario asignado si existe, sino 15 min por defecto)
        tolerancia = self.horario_asignado.tolerancia_minutos if self.horario_asignado else 15

        # Si llegó dentro de la tolerancia, no cuenta como retraso
        if diferencia <= tolerancia:
            return 0

        # Si llegó tarde, devolver los minutos de retraso
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
                        if self.hora_entrada_real:
                            # Si marcó entrada, verificar si fue en la tarde (después de 12:00)
                            if self.hora_entrada_real.hour >= 12:
                                # Marcó en su jornada laboral (tarde) - verificar si fue puntual respecto a las 14:00
                                minutos_reales = self.hora_entrada_real.hour * 60 + self.hora_entrada_real.minute
                                # Hora de referencia para la tarde: 14:00 (2 PM)
                                minutos_referencia = 14 * 60
                                diferencia = minutos_reales - minutos_referencia
                                if diferencia > self.horario_asignado.tolerancia_minutos:
                                    self.minutos_retraso = max(0, diferencia)
                                return "MEDIO_DIA"
                            else:
                                # Marcó en la mañana pero tiene permiso AM - no debería contar retraso
                                return "MEDIO_DIA"
                        else:
                            # No marcó, pero tiene medio día AM - ausente solo en la tarde
                            return "MEDIO_DIA"

                    elif permiso.jornada == 'PM':
                        # Tiene libre en la tarde, trabaja en la mañana
                        if self.hora_entrada_real:
                            # Verificar retraso solo respecto a la mañana
                            retraso = self.calcular_retraso()
                            self.minutos_retraso = retraso
                            return "MEDIO_DIA"
                        else:
                            # No marcó en la mañana - ausente
                            return "MEDIO_DIA"
                else:
                    # Día completo administrativo
                    return "DIA_ADMINISTRATIVO"

        # Verificar si hay horario excepcional
        excepcional = HorarioExcepcional.objects.filter(fecha=self.fecha).first()
        if excepcional:
            es_dia_activo = True if excepcional.hora_entrada or excepcional.hora_salida else False
        else:
            # Verificar si es día libre en su horario semanal
            dia_semana = self.fecha.weekday()
            dia_horario = self.horario_asignado.dias.filter(dia_semana=dia_semana).first()
            es_dia_activo = True
            
            if dia_horario:
                es_dia_activo = dia_horario.activo
            else:
                # Fallback lógico si no tiene configurado el DiaHorario
                es_sereno = self.funcionario.funcion == 'SERENO'
                if not es_sereno and dia_semana >= 5:
                    es_dia_activo = False

        if not es_dia_activo and not self.hora_entrada_real:
            return "DIA_LIBRE"

        # Verificar justificación manual
        if self.justificacion_manual:
            return "JUSTIFICADO"

        if not self.hora_entrada_real:
            if self.hora_salida_real:
                # Hay marcación de salida pero no de entrada - no es ausencia
                return "SIN_MARCACION_ENTRADA"
            
            # Si no hay marcación y es anterior a su fecha de ingreso, no es ausente
            if self.fecha < self.funcionario.date_joined.date():
                return "SIN_HORARIO"
                
            return "AUSENTE"

        retraso = self.calcular_retraso()
        self.minutos_retraso = retraso

        if retraso == 0:
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

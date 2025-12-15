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
        # Validar que no se creen días festivos en el pasado (opcional)
        if self.fecha < timezone.now().date():
            raise ValidationError("No se pueden crear días festivos en fechas pasadas.")

    @staticmethod
    def es_dia_festivo(fecha):
        """Verifica si una fecha es día festivo"""
        return DiaFestivo.objects.filter(fecha=fecha).exists()


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
        ("DIA_ADMINISTRATIVO", "Día Administrativo"),
        ("LICENCIA_MEDICA", "Licencia Médica"),
        ("DIA_FESTIVO", "Día Festivo"),
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
        max_length=20,
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

    def calcular_retraso(self):
        """Calcula los minutos de retraso basado en el horario asignado"""
        if not self.hora_entrada_real or not self.horario_asignado:
            return 0

        # Convertir horas a minutos desde medianoche para comparación precisa
        minutos_asignados = (self.horario_asignado.hora_entrada.hour * 60 +
                           self.horario_asignado.hora_entrada.minute)
        minutos_reales = (self.hora_entrada_real.hour * 60 +
                         self.hora_entrada_real.minute)

        # Calcular diferencia en minutos
        diferencia = minutos_reales - minutos_asignados

        # Si llegó dentro de la tolerancia, no cuenta como retraso
        if diferencia <= self.horario_asignado.tolerancia_minutos:
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

        # Si la salida es anterior a la entrada (posible error), devolver None
        if salida <= entrada:
            return None

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

    def determinar_estado(self):
        """Determina el estado basado en la hora de llegada y horario"""
        if not self.horario_asignado:
            return "SIN_HORARIO"

        # Verificar si es día festivo (prioridad máxima)
        if DiaFestivo.es_dia_festivo(self.fecha):
            return "DIA_FESTIVO"

        # Verificar primero licencia médica (prioridad alta)
        if self.tiene_licencia_medica():
            return "LICENCIA_MEDICA"

        # Verificar permiso administrativo aprobado
        if self.tiene_permiso_aprobado():
            return "DIA_ADMINISTRATIVO"

        # Verificar justificación manual
        if self.justificacion_manual:
            return "JUSTIFICADO"

        if not self.hora_entrada_real:
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

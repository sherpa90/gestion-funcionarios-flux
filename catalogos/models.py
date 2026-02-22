from django.db import models
from django.utils import timezone


class CatalogoBase(models.Model):
    """
    Modelo base abstracto para todos los catálogos del sistema.
    Proporciona campos comunes para auditoría y control.
    """
    codigo = models.CharField(max_length=20, unique=True, help_text="Código único del catálogo")
    nombre = models.CharField(max_length=100, help_text="Nombre descriptivo")
    descripcion = models.TextField(blank=True, help_text="Descripción detallada")
    activo = models.BooleanField(default=True, help_text="Si el catálogo está activo")
    orden = models.PositiveIntegerField(default=0, help_text="Orden de visualización")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['orden', 'nombre']


class RolUsuario(CatalogoBase):
    """
    Catálogo de roles de usuario del sistema.
    Normalizado de CustomUser.ROLE_CHOICES
    """
    nivel_acceso = models.PositiveIntegerField(
        default=1,
        help_text="Nivel de acceso (1=mínimo, 5=administrador)"
    )
    puede_administrar = models.BooleanField(default=False)
    puede_aprobar = models.BooleanField(default=False)
    puede_ver_todos = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Rol de Usuario"
        verbose_name_plural = "Roles de Usuarios"

    def __str__(self):
        return self.nombre


class TipoFuncionario(CatalogoBase):
    """
    Catálogo de tipos de funcionario.
    Normalizado de CustomUser.TIPO_FUNCIONARIO_CHOICES
    """
    class Meta:
        verbose_name = "Tipo de Funcionario"
        verbose_name_plural = "Tipos de Funcionarios"

    def __str__(self):
        return self.nombre


class EstadoRegistroAsistencia(CatalogoBase):
    """
    Catálogo de estados de registro de asistencia.
    Normalizado de RegistroAsistencia.ESTADO_CHOICES
    """
    ES_PUNTUAL = 'PUNTUAL'
    ES_RETRASO = 'RETRASO'
    ES_AUSENTE = 'AUSENTE'
    ES_JUSTIFICADO = 'JUSTIFICADO'
    ES_DIA_ADMINISTRATIVO = 'DIA_ADMINISTRATIVO'
    ES_LICENCIA_MEDICA = 'LICENCIA_MEDICA'
    ES_DIA_FESTIVO = 'DIA_FESTIVO'
    ES_SIN_HORARIO = 'SIN_HORARIO'

    # Campos adicionales para lógica de negocio
    cuenta_como_asistencia = models.BooleanField(default=True)
    requiere_justificacion = models.BooleanField(default=False)
    color_hex = models.CharField(max_length=7, default='#6B7280', help_text="Color para UI")

    class Meta:
        verbose_name = "Estado de Asistencia"
        verbose_name_plural = "Estados de Asistencia"
        ordering = ['orden']

    def __str__(self):
        return self.nombre


class EstadoSolicitudPermiso(CatalogoBase):
    """
    Catálogo de estados de solicitud de permiso.
    Normalizado de SolicitudPermiso.ESTADO_CHOICES
    """
    ES_PENDIENTE = 'PENDIENTE'
    ES_APROBADO = 'APROBADO'
    ES_RECHAZADO = 'RECHAZADO'
    ES_CANCELADO = 'CANCELADO'

    # Campos adicionales
    es_terminal = models.BooleanField(default=False, help_text="Estado final (no hay más transacciones)")
    permite_edicion = models.BooleanField(default=True)
    color_hex = models.CharField(max_length=7, default='#6B7280')

    class Meta:
        verbose_name = "Estado de Solicitud de Permiso"
        verbose_name_plural = "Estados de Solicitudes de Permisos"

    def __str__(self):
        return self.nombre


class TipoEquipo(CatalogoBase):
    """
    Catálogo de tipos de equipo.
    Normalizado de Equipo.TIPO_CHOICES
    """
    class Meta:
        verbose_name = "Tipo de Equipo"
        verbose_name_plural = "Tipos de Equipos"

    def __str__(self):
        return self.nombre


class EstadoEquipo(CatalogoBase):
    """
    Catálogo de estados de equipo.
    Normalizado de Equipo.ESTADO_CHOICES
    """
    ES_DISPONIBLE = 'DISPONIBLE'
    ES_ASIGNADO = 'ASIGNADO'
    ES_EN_REPARACION = 'EN_REPARACION'
    ES_BAJA = 'BAJA'

    # Campos adicionales
    disponible_prestamo = models.BooleanField(default=True)
    color_hex = models.CharField(max_length=7, default='#6B7280')

    class Meta:
        verbose_name = "Estado de Equipo"
        verbose_name_plural = "Estados de Equipos"

    def __str__(self):
        return self.nombre


class PeriodoLiquidacion(models.Model):
    """
    Catálogo de períodos para liquidaciones de sueldo.
    Permite un seguimiento más robusto de las liquidaciones.
    """
    mes = models.PositiveIntegerField(choices=[
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ])
    anio = models.PositiveIntegerField()
    fecha_inicio = models.DateField(help_text="Primer día del período")
    fecha_termino = models.DateField(help_text="Último día del período")
    activo = models.BooleanField(default=True)
    cerrado = models.BooleanField(default=False, help_text="Período cerrado para modificaciones")

    class Meta:
        verbose_name = "Período de Liquidación"
        verbose_name_plural = "Períodos de Liquidaciones"
        unique_together = ['mes', 'anio']
        ordering = ['-anio', '-mes']

    def __str__(self):
        return f"{self.get_mes_display()} {self.anio}"

    @classmethod
    def get_current_period(cls):
        """Obtiene el período actual basándose en la fecha"""
        now = timezone.now()
        return cls.objects.filter(
            mes=now.month,
            anio=now.year,
            activo=True
        ).first()


class JornadaLaboral(CatalogoBase):
    """
    Catálogo de jornadas laborales.
    Normalizado de SolicitudPermiso.jornada
    """
    ES_AM = 'AM'
    ES_PM = 'PM'
    ES_FD = 'FD'

    horas = models.FloatField(default=0, help_text="Horas que representa esta jornada")

    class Meta:
        verbose_name = "Jornada Laboral"
        verbose_name_plural = "Jornadas Laborales"

    def __str__(self):
        return self.nombre


class TipoDia(CatalogoBase):
    """
    Catálogo de tipos de día para el sistema de asistencia.
    """
    DIA_FESTIVO = 'DIA_FESTIVO'
    DIA_ADMINISTRATIVO = 'DIA_ADMINISTRATIVO'
    DIA_LICENCIA = 'DIA_LICENCIA'
    DIA_PERMISO = 'DIA_PERMISO'

    # Campos adicionales
    cuenta_como_asistencia = models.BooleanField(default=True)
    descuenta_dias = models.BooleanField(default=False)
    color_hex = models.CharField(max_length=7, default='#6B7280')

    class Meta:
        verbose_name = "Tipo de Día"
        verbose_name_plural = "Tipos de Días"

    def __str__(self):
        return self.nombre

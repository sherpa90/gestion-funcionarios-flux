from django.contrib.auth.models import AbstractUser
from django.db import models
from core.validators import validate_run
from core.utils import clean_rut_for_matching


class GrupoCorreo(models.Model):
    """Modelo para grupos de correo institucionales"""
    
    nombre = models.CharField(max_length=100, unique=True, help_text="Nombre del grupo de correo")
    correo = models.EmailField(unique=True, help_text="Correo del grupo (ej: grupo@dominio.cl)")
    descripcion = models.TextField(blank=True, help_text="Descripción del propósito del grupo")
    miembros = models.ManyToManyField(
        'CustomUser', 
        related_name='grupos_correo',
        blank=True,
        help_text="Miembros del grupo"
    )
    creado_por = models.ForeignKey(
        'CustomUser', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='grupos_creados'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Grupo de Correo"
        verbose_name_plural = "Grupos de Correo"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.correo})"

    @property
    def cantidad_miembros(self):
        return self.miembros.count()


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('FUNCIONARIO', 'Funcionario'),
        ('DIRECTOR', 'Director'),
        ('DIRECTIVO', 'Directivo'),
        ('SECRETARIA', 'Secretaria'),
        ('ADMIN', 'Administrador'),
    ]

    TIPO_FUNCIONARIO_CHOICES = [
        ('DOCENTE', 'Docente'),
        ('ASISTENTE', 'Asistente de la Educación'),
    ]

    FUNCION_CHOICES = [
        ('ASISTENTE_AULA', 'Asistente de Aula'),
        ('ASISTENTE_REEMPLAZO', 'Asistente Reemplazo'),
        ('ASISTENTE_SOCIAL', 'Asistente Social'),
        ('AUXILIAR', 'Auxiliar'),
        ('AYUDANTE_BIBLIOTECA', 'Ayudante de Biblioteca'),
        ('DIRECTOR', 'Director (a)'),
        ('DOCENTE_AULA', 'Docente de Aula'),
        ('DOCENTE_DIFERENCIAL', 'Docente Diferencial'),
        ('DOCENTE_REEMPLAZO', 'Docente Reemplazo'),
        ('EDUCADORA_DIFERENCIAL', 'Educadora Diferencial'),
        ('EDUCADORA_PARVULOS', 'Educadora de Párvulos'),
        ('ENCARGADO_BIBLIOTECA', 'Encargado (a) de Biblioteca'),
        ('ENCARGADO_CONVIVENCIA', 'Encargado (a) de Convivencia'),
        ('ENCARGADO_FOTOCOPIA', 'Encargado de Fotocopia'),
        ('ENFERMERO', 'Enfermero (a)'),
        ('FONOAUDIOLOGO', 'Fonoaudiólogo (a)'),
        ('INFORMATICO', 'Informático'),
        ('INSPECTOR', 'Inspector (a)'),
        ('INSPECTOR_GENERAL', 'Inspector General'),
        ('JEFE_UTP', 'Jefe (a) de UTP'),
        ('MONITOR_TALLER', 'Monitor Taller'),
        ('PSICOPEDAGOGO', 'Psicopedagogo (a)'),
        ('PSICOLOGO', 'Psicólogo (a)'),
        ('SECRETARIA', 'Secretaria'),
        ('SERENO', 'Sereno'),
        ('TECNICO_DEPORTIVO', 'Técnico Deportivo'),
        ('TECNICO_DIFERENCIAL', 'Técnico Diferencial'),
        ('TECNICO_PARSULO', 'Técnico en Párvulo'),
        ('TERAPEUTA_OCUPACIONAL', 'Terapeuta Ocupacional'),
    ]

    email = models.EmailField(unique=True, null=True, blank=False, help_text="Correo electrónico de acceso")
    run = models.CharField(
        max_length=12, 
        unique=True, 
        validators=[validate_run],
        help_text="Formato: 12345678-K"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='FUNCIONARIO')
    tipo_funcionario = models.CharField(
        max_length=20, 
        choices=TIPO_FUNCIONARIO_CHOICES, 
        blank=True, 
        null=True,
        help_text="Aplica solo para rol Funcionario"
    )
    funcion = models.CharField(
        max_length=30,
        choices=FUNCION_CHOICES,
        blank=True,
        null=True,
        help_text="Función o cargo específico del usuario"
    )
    dias_disponibles = models.FloatField(default=6.0)
    telefono = models.CharField(max_length=20, blank=True, help_text="Teléfono de contacto")
    is_blocked = models.BooleanField(default=False, help_text="Si está marcado, el usuario no podrá iniciar sesión")
    blocked_at = models.DateTimeField(null=True, blank=True, help_text="Fecha en que fue bloqueado el usuario")
    blocked_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blocked_users',
        help_text="Usuario que realizó el bloqueo"
    )
    is_on_leave = models.BooleanField(default=False, help_text="Si está marcado, el funcionario está de baja")
    baja_date = models.DateField(null=True, blank=True, help_text="Fecha de inicio de la baja")
    alta_date = models.DateField(null=True, blank=True, help_text="Fecha de alta/reingreso")
    notifications_disabled = models.BooleanField(default=False, help_text="Si está marcado, se silenciarán las notificaciones por correo")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['run', 'first_name', 'last_name']

    @property
    def dias_disponibles_pct(self):
        """Calcula el porcentaje de días disponibles (máximo 6.0)"""
        try:
            return min(round((self.dias_disponibles / 6.0) * 100, 1), 100)
        except (TypeError, ZeroDivisionError):
            return 0

    def recalculate_dias_disponibles(self):
        """Recalcula los días disponibles restando los permisos APROBADOS del año actual."""
        if not self.is_active:
            return self.dias_disponibles
            
        from permisos.models import SolicitudPermiso
        from django.db.models import Sum
        from django.utils import timezone
        
        current_year = timezone.now().year
        total_aprobados = SolicitudPermiso.objects.filter(
            usuario=self, 
            estado='APROBADO',
            fecha_inicio__year=current_year
        ).aggregate(total=Sum('dias_solicitados'))['total'] or 0.0
        
        self.dias_disponibles = max(0.0, 6.0 - float(total_aprobados))
        self.save()
        return self.dias_disponibles

    def is_on_baja_on_date(self, fecha):
        """Verifica si el funcionario está de baja en una fecha específica.
        
        Considera tanto la baja global (is_on_leave, baja_date, alta_date) 
        como los periodos de baja específicos definidos en BajaPeriodo.
        """
        from django.utils import timezone
        
        # Verificar periodos de baja específicos primero
        for periodo in self.baja_periodos.filter(estado='ACTIVO'):
            if periodo.fecha_inicio <= fecha:
                if periodo.fecha_termino is None or fecha <= periodo.fecha_termino:
                    return True
        
        # Verificar baja global
        if self.is_on_leave or self.baja_date:
            if self.alta_date and fecha >= self.alta_date:
                return False
            return self.baja_date is not None and fecha >= self.baja_date
        
        return False

    def save(self, *args, **kwargs):
        # Normalizar el RUT antes de guardar (con puntos para formato chileno)
        if self.run:
            from core.utils import normalize_rut
            self.run = normalize_rut(self.run)
        
        # Determinar si es un nuevo usuario
        is_new = self.pk is None
        
        # Guardar el usuario primero
        super().save(*args, **kwargs)
        
        # Si es un nuevo usuario, crear horario por defecto
        if is_new:
            try:
                from asistencia.models import HorarioFuncionario
                from datetime import time
                # Verificar si ya existe un horario
                if not HorarioFuncionario.objects.filter(funcionario=self).exists():
                    HorarioFuncionario.objects.create(
                        funcionario=self,
                        hora_entrada=time(7, 45),
                        activo=True
                    )
            except Exception as e:
                print(f"Error al crear horario para {self.get_full_name()}: {e}")

    @property
    def categoria_funcionario(self):
        """Determina la categoría del funcionario para estadísticas"""
        if self.role in ['DIRECTOR', 'DIRECTIVO', 'SECRETARIA', 'ADMIN']:
            return 'ADMINISTRATIVO'
        elif self.tipo_funcionario == 'DOCENTE' or (self.funcion and 'DOCENTE' in self.funcion):
            return 'DOCENTE'
        elif self.tipo_funcionario == 'ASISTENTE' or (self.funcion and any(term in self.funcion for term in ['ASISTENTE', 'TECNICO', 'AUXILIAR', 'ENCARGADO', 'INSPECTOR', 'JEFE', 'PSICOPEDAGOGO', 'PSICOLOGO', 'FONOAUDIOLOGO', 'TERAPEUTA', 'ENFERMERO', 'SERENO', 'INFORMATICO', 'MONITOR', 'TALLER'])):
            return 'ASISTENTE'
        else:
            return 'OTRO'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.run})"

    def esta_ausente(self):
        """Determina si el usuario debería contarse como ausente en reportes.
        
        Un usuario es considerado ausente si está actualmente empleado (is_active=True)
        y está de baja (is_on_leave=True).
        
        Esto asegura que los trabajadores de reemplazo cuyo contrato ha terminado
        (is_active=False) no se cuenten como ausentes, incluso si is_on_leave 
        estuviera establecido en True (lo cual no debería ocurrir en casos normales
        de término de contrato).
        """
        return self.is_active and self.is_on_leave

    def es_dia_activo(self, fecha):
        """
        Determina si una fecha dada es un día laboral activo para el funcionario.
        """
        from asistencia.models import HorarioFuncionario, DiaHorario, HorarioExcepcional
        
        # Primero, obtener su horario activo
        horario_actual = HorarioFuncionario.objects.filter(
            funcionario=self, activo=True
        ).first()
        
        dia_semana = fecha.weekday()
        
        # Determinar si es sereno
        es_sereno = (
            getattr(self, 'funcion', None) == 'SERENO' or
            getattr(self, 'tipo_funcionario', None) == 'SERENO' or
            getattr(self, 'role', None) == 'SERENO'
        )
        
        if horario_actual:
            semana_t = DiaHorario.get_semana_tipo(fecha, self)
            
            # Buscar primero horario específico para esta semana (1 o 2)
            dia_horario = horario_actual.dias.filter(
                dia_semana=dia_semana, 
                semana_tipo=semana_t
            ).first()
            
            if not dia_horario:
                dia_horario = horario_actual.dias.filter(
                    dia_semana=dia_semana, 
                    semana_tipo__isnull=True
                ).first()
            
            if dia_horario:
                es_dia_activo_base = dia_horario.activo
            else:
                es_dia_activo_base = True if es_sereno else dia_semana < 5
        else:
            es_dia_activo_base = True if es_sereno else dia_semana < 5
            
        # Verificar si hay horario excepcional
        excepcional = HorarioExcepcional.objects.filter(fecha=fecha).first()
        if excepcional and excepcional.aplica_a_funcionario(self):
            if excepcional.hora_entrada:
                return True
            else:
                return es_dia_activo_base
        else:
            return es_dia_activo_base



class BajaPeriodo(models.Model):
    """Periodo de baja para funcionarios (útil para reemplazos temporales)"""
    
    ESTADO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
    ]
    
    MOTIVO_CHOICES = [
        ('Reemplazo', 'Reemplazo'),
        ('Licencia', 'Licencia'),
        ('Baja médica', 'Baja médica'),
        ('Vacaciones', 'Vacaciones'),
        ('Capacitación', 'Capacitación'),
        ('Otro', 'Otro'),
    ]
    
    usuario = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='baja_periodos',
        help_text="Funcionario al que se aplica este período de baja"
    )
    motivo = models.CharField(max_length=100, choices=MOTIVO_CHOICES, help_text="Motivo de la baja")
    fecha_inicio = models.DateField(help_text="Fecha de inicio de la baja")
    fecha_termino = models.DateField(null=True, blank=True, help_text="Fecha de fin de la baja (opcional si es indefinida)")
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='ACTIVO')
    justificacion = models.TextField(blank=True, help_text="Justificación adicional")
    creado_por = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='bajas_creadas',
        limit_choices_to={'role__in': ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']}
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Periodo de Baja"
        verbose_name_plural = "Periodos de Baja"
        ordering = ['-fecha_inicio']
        constraints = [
            models.CheckConstraint(
                check=models.Q(fecha_termino__isnull=True) | models.Q(fecha_termino__gte=models.F('fecha_inicio')),
                name='check_fecha_termino_gte_inicio'
            )
        ]
    
    def __str__(self):
        estado_str = "hasta" if self.fecha_termino else "(indefinido)"
        return f"{self.usuario.get_full_name()} - {self.motivo} ({self.fecha_inicio} {estado_str} {self.fecha_termino or ''})"
    
    @property
    def activo(self):
        """Verifica si el período está activo"""
        from django.utils import timezone
        hoy = timezone.now().date()
        return self.estado == 'ACTIVO' and self.fecha_inicio <= hoy and (self.fecha_termino is None or hoy <= self.fecha_termino)


class DirectorioTelefonico(models.Model):
    """Modelo para el directorio telefónico institucional"""
    
    lugar = models.CharField(max_length=100, help_text="Nombre del lugar (ej: Dirección, Secretarias, Biblioteca)")
    anexo = models.CharField(max_length=20, unique=True, help_text="Número de anexo (ej: 101, 202)")
    descripcion = models.TextField(blank=True, help_text="Descripción adicional")
    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(
        'CustomUser', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='directorio_creado'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Directorio Telefónico"
        verbose_name_plural = "Directorio Telefónico"
        ordering = ['lugar']

    def __str__(self):
        return f"{self.lugar} - {self.anexo}"

from auditlog.registry import auditlog
auditlog.register(CustomUser)

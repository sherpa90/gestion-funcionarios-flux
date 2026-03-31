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
                        tolerancia_minutos=5,
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
        elif self.tipo_funcionario == 'ASISTENTE' or (self.funcion and any(term in self.funcion for term in ['ASISTENTE', 'TECNICO', 'AUXILIAR', 'ENCARGADO', 'INSPECTOR', 'JEFE', 'PSICOPEDAGOGO', 'PSICOLOGO', 'FONOAUDIOLOGO', 'TERAPEUTA', 'ENFERMERO', 'SERENO', 'INFORMATICO'])):
            return 'ASISTENTE'
        else:
            return 'OTRO'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.run})"


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

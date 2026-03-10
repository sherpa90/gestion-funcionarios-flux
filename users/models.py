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
    dias_disponibles = models.FloatField(default=6.0)
    telefono = models.CharField(max_length=20, blank=True, help_text="Teléfono de contacto")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['run', 'first_name', 'last_name']

    @property
    def dias_disponibles_pct(self):
        """Calcula el porcentaje de días disponibles (máximo 6.0)"""
        try:
            return min(round((self.dias_disponibles / 6.0) * 100, 1), 100)
        except (TypeError, ZeroDivisionError):
            return 0

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

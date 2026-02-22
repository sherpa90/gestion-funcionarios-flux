from django.contrib.auth.models import AbstractUser
from django.db import models
from core.validators import validate_run
from core.utils import clean_rut_for_matching

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
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.run})"

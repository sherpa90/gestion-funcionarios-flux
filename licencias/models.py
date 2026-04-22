from django.db import models
from django.conf import settings

class LicenciaMedica(models.Model):
    TIPO_CHOICES = [
        ('LICENCIA', 'Licencia Médica'),
        ('PERMISO', 'Permiso sin Goce de Remuneraciones'),
    ]
    
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='licencias')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='LICENCIA')
    fecha_inicio = models.DateField()
    dias = models.PositiveIntegerField()
    archivo = models.FileField(upload_to='licencias/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='licencias_creadas', help_text="Usuario que registró la licencia")

    @property
    def fecha_termino(self):
        """Calcula la fecha de término basada en la fecha de inicio y la cantidad de días."""
        from datetime import timedelta
        if self.fecha_inicio and self.dias:
            return self.fecha_inicio + timedelta(days=self.dias - 1)
        return self.fecha_inicio

    def __str__(self):
        return f"{self.usuario} - {self.fecha_inicio} ({self.dias} días)"

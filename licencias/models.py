from django.db import models
from django.conf import settings

class LicenciaMedica(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='licencias')
    fecha_inicio = models.DateField()
    dias = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='licencias_creadas', help_text="Usuario que registró la licencia")

    def __str__(self):
        return f"{self.usuario} - {self.fecha_inicio} ({self.dias} días)"

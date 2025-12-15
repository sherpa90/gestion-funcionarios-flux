from django.db import models
from django.conf import settings

class Liquidacion(models.Model):
    funcionario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='liquidaciones')
    archivo = models.FileField(upload_to='liquidaciones/%Y/%m/')
    mes = models.IntegerField()
    anio = models.IntegerField()
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-anio', '-mes']
        verbose_name = 'Liquidación de Sueldo'
        verbose_name_plural = 'Liquidaciones de Sueldo'

    def __str__(self):
        return f"Liquidación {self.mes}/{self.anio} - {self.funcionario}"

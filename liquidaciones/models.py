from django.db import models
from django.conf import settings

# Meses en español
MESES_CHOICES = [
    (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
    (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
    (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
]

def get_mes_nombre(mes_num):
    """Convierte el número del mes a nombre en español"""
    return dict(MESES_CHOICES).get(mes_num, '')

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

    @property
    def mes_nombre(self):
        """Retorna el nombre del mes en español"""
        return get_mes_nombre(self.mes)

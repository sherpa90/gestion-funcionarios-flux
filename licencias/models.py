from django.db import models
from django.conf import settings
from core.storage import EncryptedFileSystemStorage

class LicenciaMedica(models.Model):
    TIPO_CHOICES = [
        ('LICENCIA', 'Licencia Médica'),
        ('PERMISO', 'Permiso sin Goce de Remuneraciones'),
        ('PRENATAL', 'Licencia Prenatal'),
        ('POSTNATAL', 'Licencia Postnatal'),
        ('POSTNATAL_PARENTAL', 'Permiso Postnatal Parental'),
        ('FALLECIMIENTO', 'Licencia por Fallecimiento'),
    ]

    # Tipos cuya duración se cuenta en días hábiles (L-V, sin feriados)
    TIPOS_DIAS_HABILES = {'FALLECIMIENTO'}

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='licencias')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='LICENCIA')
    fecha_inicio = models.DateField()
    dias = models.PositiveIntegerField(help_text="Para Licencia por Fallecimiento, se cuentan días hábiles (lunes a viernes, sin feriados).")
    archivo = models.FileField(upload_to='licencias/', storage=EncryptedFileSystemStorage(), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='licencias_creadas', help_text="Usuario que registró la licencia")

    @property
    def usa_dias_habiles(self):
        """Indica si este tipo de licencia usa días hábiles para el cálculo de duración."""
        return self.tipo in self.TIPOS_DIAS_HABILES

    @property
    def fecha_termino(self):
        """Calcula la fecha de término basada en la fecha de inicio y la cantidad de días.
        
        Para Licencia por Fallecimiento, se cuentan únicamente días hábiles
        (lunes a viernes, excluyendo feriados registrados en el sistema).
        Para el resto de tipos, se cuentan días calendario.
        """
        from datetime import timedelta
        if not self.fecha_inicio or not self.dias:
            return self.fecha_inicio

        if self.usa_dias_habiles:
            try:
                from core.services import BusinessDayCalculator
                return BusinessDayCalculator.calculate_end_date(self.fecha_inicio, self.dias)
            except Exception:
                # Fallback a días calendario si hay algún error inesperado
                return self.fecha_inicio + timedelta(days=self.dias - 1)

        return self.fecha_inicio + timedelta(days=self.dias - 1)

    def __str__(self):
        return f"{self.usuario} - {self.fecha_inicio} ({self.dias} días)"

from auditlog.registry import auditlog
auditlog.register(LicenciaMedica)

from django.db import models
from django.conf import settings
from django.utils import timezone

class SolicitudPermiso(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
        ('CANCELADO', 'Cancelado'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='solicitudes')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_creadas')
    fecha_inicio = models.DateField()
    dias_solicitados = models.FloatField(choices=[(0.5, '0.5'), (1.0, '1.0'), (1.5, '1.5'), (2.0, '2.0'), (2.5, '2.5'), (3.0, '3.0')])
    jornada = models.CharField(
        max_length=2,
        choices=[('AM', 'Mañana'), ('PM', 'Tarde'), ('FD', 'Día Completo')],
        default='FD',
        help_text="Jornada del permiso (solo aplica para medio día)"
    )
    fecha_termino = models.DateField(blank=True, null=True) # Calculado
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    observacion = models.TextField(blank=True, help_text="Motivo o justificación de la solicitud")
    motivo_rechazo = models.TextField(blank=True, help_text="Razón del rechazo (solo si es rechazado)")
    motivo_cancelacion = models.TextField(blank=True, help_text="Razón de la cancelación (solo si es cancelado)")
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_canceladas')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    archivo_justificacion = models.FileField(upload_to='solicitudes/', blank=True, null=True, help_text="Documento de respaldo (PDF o JPG)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.usuario} - {self.fecha_inicio} ({self.dias_solicitados} días)"

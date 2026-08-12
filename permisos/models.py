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
    aprobado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_aprobadas')
    archivo_justificacion = models.FileField(upload_to='solicitudes/', blank=True, null=True, help_text="Documento de respaldo (PDF o JPG)")
    is_unlocked = models.BooleanField(default=False, help_text="Indica si un permiso fuera de plazo ha sido desbloqueado por un directivo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.usuario} - {self.fecha_inicio} ({self.dias_solicitados} días)"

    @property
    def es_fuera_de_plazo(self):
        """Devuelve True si la solicitud se hizo con menos de 2 días de anticipación."""
        if not self.fecha_inicio:
            return False
        
        from django.utils import timezone
        base_date = self.created_at.date() if self.created_at else timezone.now().date()
        dias_diferencia = (self.fecha_inicio - base_date).days
        return dias_diferencia < 2

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        estado_anterior = None
        if not is_new:
            try:
                estado_anterior = SolicitudPermiso.objects.get(pk=self.pk).estado
            except SolicitudPermiso.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        # Sincronizar registros de asistencia si el estado cambió a/desde APROBADO,
        # o si se creó aprobado (raro pero posible).
        if is_new or estado_anterior != self.estado:
            # Solo actualizar si involucra APROBADO (ya sea antes o ahora) para optimizar
            if self.estado == 'APROBADO' or estado_anterior == 'APROBADO':
                from asistencia.models import RegistroAsistencia
                from datetime import timedelta
                
                if self.fecha_inicio and self.fecha_termino:
                    fecha = self.fecha_inicio
                    while fecha <= self.fecha_termino:
                        # Buscar si existe el registro para esa fecha
                        registro = RegistroAsistencia.objects.filter(
                            funcionario=self.usuario, 
                            fecha=fecha
                        ).first()
                        
                        if registro:
                            # Al llamar save() se dispara determinar_estado()
                            registro.save()
                        fecha += timedelta(days=1)

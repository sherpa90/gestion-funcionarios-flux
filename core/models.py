from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.timestamp} - {self.actor} - {self.action}"


class SystemSettings(models.Model):
    notifications_enabled = models.BooleanField(default=True, help_text="Desactivando silencia todas las notificaciones por correo")
    liquidations_notifications_enabled = models.BooleanField(default=True, help_text="Notificar cuando se suben liquidaciones")
    attendance_notifications_enabled = models.BooleanField(default=True, help_text="Notificar cuando se cargan asistencias")
    director_daily_summary_enabled = models.BooleanField(default=False, help_text="Enviar resumen diario de días administrativos y licencias a directores")
    director_daily_summary_time = models.CharField(max_length=5, default='07:45', help_text="Hora de envío del resumen diario (HH:MM)")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración del Sistema"
        verbose_name_plural = "Configuraciones del Sistema"

    def __str__(self):
        return "Configuración del Sistema"

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

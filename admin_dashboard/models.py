from django.db import models
from django.conf import settings
from django.utils import timezone


class SystemLog(models.Model):
    TIPO_CHOICES = [
        ('AUTH', 'Autenticación'),
        ('CREATE', 'Creación'),
        ('UPDATE', 'Actualización'),
        ('DELETE', 'Eliminación'),
        ('APPROVE', 'Aprobación'),
        ('REJECT', 'Rechazo'),
        ('ERROR', 'Error'),
        ('EXPORT', 'Exportación'),
        ('IMPORT', 'Importación'),
    ]
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='system_logs'
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    accion = models.CharField(max_length=255)
    descripcion = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Log del Sistema'
        verbose_name_plural = 'Logs del Sistema'
        indexes = [
            models.Index(fields=['-timestamp', 'tipo']),
            models.Index(fields=['usuario', '-timestamp']),
        ]
    
    def __str__(self):
        usuario_str = self.usuario.get_full_name() if self.usuario else 'Sistema'
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M')} - {usuario_str}: {self.accion}"


class ImportacionUsuarios(models.Model):
    archivo = models.FileField(upload_to='imports/usuarios/%Y/%m/')
    importado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='importaciones'
    )
    fecha_importacion = models.DateTimeField(default=timezone.now)
    total_registros = models.IntegerField(default=0)
    exitosos = models.IntegerField(default=0)
    fallidos = models.IntegerField(default=0)
    log_errores = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-fecha_importacion']
        verbose_name = 'Importación de Usuarios'
        verbose_name_plural = 'Importaciones de Usuarios'
    
    def __str__(self):
        return f"Importación {self.id} - {self.fecha_importacion.strftime('%Y-%m-%d')} ({self.exitosos}/{self.total_registros})"
    
    @property
    def tasa_exito(self):
        if self.total_registros == 0:
            return 0
        return round((self.exitosos / self.total_registros) * 100, 2)

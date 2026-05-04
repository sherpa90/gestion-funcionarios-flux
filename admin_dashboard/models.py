from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import urllib.parse

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


class Efemeride(models.Model):
    titulo = models.CharField(max_length=255, verbose_name='Actividad o Conmemoración')
    fecha = models.DateField(verbose_name='Fecha')
    fecha_hasta = models.DateField(verbose_name='Fecha Hasta', null=True, blank=True)
    responsable = models.CharField(max_length=255, blank=True, null=True, verbose_name='Responsable')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripción')
    
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='efemerides_creadas'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha']
        verbose_name = 'Efeméride'
        verbose_name_plural = 'Efemérides'

    def __str__(self):
        if self.fecha_hasta:
            return f"{self.fecha} al {self.fecha_hasta} - {self.titulo}"
        return f"{self.fecha} - {self.titulo}"

    @property
    def google_calendar_url(self):
        base_url = "https://www.google.com/calendar/render?action=TEMPLATE"
        date_start = self.fecha.strftime('%Y%m%d')
        
        if self.fecha_hasta:
            # Google Calendar end date is exclusive for all-day events
            date_end = (self.fecha_hasta + timedelta(days=1)).strftime('%Y%m%d')
        else:
            date_end = (self.fecha + timedelta(days=1)).strftime('%Y%m%d')
            
        details = f"Responsable: {self.responsable or 'No especificado'}\n{self.descripcion or ''}"
        params = {
            'text': self.titulo,
            'dates': f"{date_start}/{date_end}",
            'details': details,
        }
        return f"{base_url}&{urllib.parse.urlencode(params)}"

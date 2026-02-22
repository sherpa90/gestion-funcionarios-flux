from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Equipo(models.Model):
    """Modelo para gestionar equipos tecnológicos"""
    
    TIPO_CHOICES = [
        ('LAPTOP', 'Laptop'),
        ('DESKTOP', 'Computador de Escritorio'),
        ('TABLET', 'Tablet'),
        ('IMPRESORA', 'Impresora'),
        ('MONITOR', 'Monitor'),
        ('PROYECTOR', 'Proyector'),
        ('CELULAR', 'Celular'),
        ('OTRO', 'Otro'),
    ]
    
    ESTADO_CHOICES = [
        ('DISPONIBLE', 'Disponible'),
        ('ASIGNADO', 'Asignado'),
        ('EN_REPARACION', 'En Reparación'),
        ('BAJA', 'De Baja'),
    ]
    
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        verbose_name='Tipo de Equipo'
    )
    marca = models.CharField(
        max_length=100,
        verbose_name='Marca'
    )
    modelo = models.CharField(
        max_length=100,
        verbose_name='Modelo'
    )
    numero_serie = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Número de Serie'
    )
    numero_inventario = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Número de Inventario'
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='DISPONIBLE',
        verbose_name='Estado'
    )
    fecha_adquisicion = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Adquisición'
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='equipos_creados'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Equipo'
        verbose_name_plural = 'Equipos'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.marca} {self.modelo} - {self.numero_inventario}"
    
    def save(self, *args, **kwargs):
        # Ejecutar validación completa
        self.full_clean()
        super().save(*args, **kwargs)
    
    def clean(self):
        if self.numero_serie:
            # Verificar que no contenga caracteres de plantilla Django
            if '{{' in self.numero_serie or '}}' in self.numero_serie:
                raise ValidationError('El número de serie no puede contener caracteres de plantilla.')
            self.numero_serie = self.numero_serie.upper()
        if self.numero_inventario:
            # Verificar que no contenga caracteres de plantilla Django
            if '{{' in self.numero_inventario or '}}' in self.numero_inventario:
                raise ValidationError('El número de inventario no puede contener caracteres de plantilla.')
            self.numero_inventario = self.numero_inventario.upper()


class PrestamoEquipo(models.Model):
    """Modelo para registrar préstamos de equipos"""
    
    equipo = models.ForeignKey(
        Equipo,
        on_delete=models.CASCADE,
        related_name='prestamos'
    )
    funcionario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='equipos_prestados'
    )
    fecha_asignacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Asignación'
    )
    fecha_devolucion = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Devolución'
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones del Préstamo'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Préstamo Activo'
    )
    asignado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='prestamos_asignados'
    )
    
    class Meta:
        verbose_name = 'Préstamo de Equipo'
        verbose_name_plural = 'Préstamos de Equipos'
        ordering = ['-fecha_asignacion']
    
    def __str__(self):
        return f"{self.equipo} -> {self.funcionario}"
    
    def save(self, *args, **kwargs):
        # Actualizar estado del equipo
        if self.activo:
            self.equipo.estado = 'ASIGNADO'
            self.equipo.save()
        else:
            if self.fecha_devolucion:
                self.equipo.estado = 'DISPONIBLE'
                self.equipo.save()
        super().save(*args, **kwargs)


class FallaEquipo(models.Model):
    """Modelo para registrar fallas o averías en los equipos reportadas por funcionarios"""
    
    ESTADO_FALLA_CHOICES = [
        ('REPORTADA', 'Reportada'),
        ('EN_REVISION', 'En Revisión'),
        ('REPARADA', 'Reparada'),
        ('BAJA', 'De Baja / Reemplazo'),
        ('DENEGADA', 'No Procede'),
    ]

    equipo = models.ForeignKey(
        Equipo, 
        on_delete=models.CASCADE, 
        related_name='fallas',
        verbose_name='Equipo'
    )
    funcionario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='fallas_reportadas',
        verbose_name='Funcionario que Reporta'
    )
    descripcion = models.TextField(
        verbose_name='Descripción de la Falla'
    )
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_FALLA_CHOICES, 
        default='REPORTADA',
        verbose_name='Estado de la Falla'
    )
    comentarios_tecnicos = models.TextField(
        blank=True, 
        verbose_name='Comentarios Técnicos / Resolución'
    )
    fecha_reporte = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Reporte'
    )
    fecha_resolucion = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='Fecha de Resolución'
    )
    resuelto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='fallas_resueltas',
        verbose_name='Resuelto por'
    )

    class Meta:
        verbose_name = 'Falla de Equipo'
        verbose_name_plural = 'Fallas de Equipos'
        ordering = ['-fecha_reporte']

    def __str__(self):
        return f"Falla en {self.equipo} ({self.get_estado_display()})"

    def save(self, *args, **kwargs):
        # Si el estado cambia a Reparada o Baja, y no hay fecha de resolución, poner la actual
        if self.estado in ('REPARADA', 'BAJA', 'DENEGADA') and not self.fecha_resolucion:
            from django.utils import timezone
            self.fecha_resolucion = timezone.now()
            
        # Si el equipo está en reparación por esta falla, actualizar el estado del equipo
        if self.estado == 'EN_REVISION':
            self.equipo.estado = 'EN_REPARACION'
            self.equipo.save()
        elif self.estado == 'REPARADA':
            self.equipo.estado = 'ASIGNADO'
            self.equipo.save()
        elif self.estado == 'BAJA':
            self.equipo.estado = 'BAJA'
            self.equipo.save()
            
        super().save(*args, **kwargs)

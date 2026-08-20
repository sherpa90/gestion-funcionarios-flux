from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class LugarEquipo(models.Model):
    """Modelo para gestionar lugares/ubicaciones de equipos"""
    
    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre del Lugar'
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='lugares_equipos_creados'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Lugar de Equipo'
        verbose_name_plural = 'Lugares de Equipos'
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre
    
    def save(self, *args, **kwargs):
        self.nombre = self.nombre.strip().upper()
        super().save(*args, **kwargs)
    
    def clean(self):
        if self.nombre:
            self.nombre = self.nombre.strip().upper()
            if '{{' in self.nombre or '}}' in self.nombre:
                raise ValidationError('El nombre del lugar no puede contener caracteres de plantilla.')


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
        ('CONTROL_REMOTO', 'Control Remoto'),
        ('PARLANTE', 'Parlante'),
        ('LAPIZ_INTERACTIVO', 'Lápiz Interactivo'),
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
        null=True,
        blank=True,
        verbose_name='Modelo'
    )
    numero_serie = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Número de Serie'
    )
    numero_inventario = models.CharField(
        max_length=100,
        null=True,
        blank=True,
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
    fecha_origen = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Origen'
    )
    lugar = models.ForeignKey(
        LugarEquipo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipos',
        verbose_name='Lugar'
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
        desc = f"{self.marca}"
        if self.modelo:
            desc += f" {self.modelo}"
        if self.numero_inventario:
            desc += f" - #{self.numero_inventario}"
        elif self.numero_serie:
            desc += f" - SN: {self.numero_serie}"
        return desc
    
    def validate_unique(self, exclude=None):
        """Validación personalizada para permitir múltiples equipos sin número de serie/inventario."""
        if exclude is None:
            exclude = set()
        else:
            exclude = set(exclude)
        
        # No validar unicidad si los campos están vacíos
        if not self.numero_serie:
            exclude.add('numero_serie')
        if not self.numero_inventario:
            exclude.add('numero_inventario')
        
        super().validate_unique(exclude=exclude)
    
    def save(self, *args, **kwargs):
        # Ejecutar validación completa
        self.full_clean()
        super().save(*args, **kwargs)
    
    def clean(self):
        if self.numero_serie:
            # Verificar que el número de serie sea único
            if Equipo.objects.filter(numero_serie=self.numero_serie).exclude(pk=self.pk).exists():
                raise ValidationError('El número de serie ya está registrado en otro equipo.')
            # Verificar que no contenga caracteres de plantilla Django
            if '{{' in self.numero_serie or '}}' in self.numero_serie:
                raise ValidationError('El número de serie no puede contener caracteres de plantilla.')
            self.numero_serie = self.numero_serie.upper()
        if self.numero_inventario:
            # Verificar que el número de inventario sea único
            if Equipo.objects.filter(numero_inventario=self.numero_inventario).exclude(pk=self.pk).exists():
                raise ValidationError('El número de inventario ya está registrado en otro equipo.')
            # Verificar que no contenga caracteres de plantilla Django
            if '{{' in self.numero_inventario or '}}' in self.numero_inventario:
                raise ValidationError('El número de inventario no puede contener caracteres de plantilla.')
            self.numero_inventario = self.numero_inventario.upper()


class PrestamoEquipo(models.Model):
    """Modelo para registrar préstamos de equipos (permanentes o diarios)"""
    
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
    fecha_devolucion_real = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha y Hora de Devolución Real'
    )
    es_prestamo_diario = models.BooleanField(
        default=False,
        verbose_name='¿Es Préstamo Diario?'
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
        tipo_str = " (Diario)" if self.es_prestamo_diario else ""
        return f"{self.equipo} -> {self.funcionario}{tipo_str}"
    
    def save(self, *args, **kwargs):
        # Actualizar estado del equipo
        if self.activo:
            self.equipo.estado = 'ASIGNADO'
            self.equipo.save()
        else:
            if self.fecha_devolucion or self.fecha_devolucion_real:
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


class HitoMantenimiento(models.Model):
    """Modelo para registrar hitos o mantenimientos a los equipos"""
    
    TIPO_HITO_CHOICES = [
        ('MANTENIMIENTO_PREVENTIVO', 'Mantenimiento Preventivo'),
        ('REPARACION', 'Reparación / Mantenimiento Correctivo'),
        ('ACTUALIZACION', 'Actualización de Hardware/Software'),
        ('INSPECCION', 'Inspección Rutinaria'),
        ('OTRO', 'Otro / Observación'),
    ]

    equipo = models.ForeignKey(
        Equipo,
        on_delete=models.CASCADE,
        related_name='hitos'
    )
    tipo = models.CharField(
        max_length=50,
        choices=TIPO_HITO_CHOICES,
        verbose_name='Tipo de Mantenimiento / Hito'
    )
    fecha = models.DateField(
        verbose_name='Fecha del Hito'
    )
    descripcion = models.TextField(
        verbose_name='Descripción / Observaciones'
    )
    costo = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name='Costo Asociado (Opcional)'
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='hitos_creados'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-fecha_creacion']
        verbose_name = 'Hito de Mantenimiento'
        verbose_name_plural = 'Hitos de Mantenimiento'

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.equipo} ({self.fecha})"


class TicketBitacora(models.Model):
    """Modelo para el Sistema de Tickets y Bitácora General de Actividades TI"""
    
    CATEGORIA_CHOICES = [
        ('SOPORTE_FUNCIONARIO', 'Soporte a Funcionario'),
        ('MANTENIMIENTO_EQUIPO', 'Mantenimiento / Reparación de Equipo'),
        ('AUDIOVISUAL_SALAS', 'Configuración / Instalación Audiovisual'),
        ('REDES_CONECTIVIDAD', 'Redes / Conectividad / Wifi'),
        ('SOFTWARE_PLATAFORMAS', 'Software / Cuentas / Plataformas'),
        ('IMPRESION_FOTOCOPIA', 'Impresión / Escáner / Fotocopia'),
        ('REVISION_PREVENTIVA', 'Revisión Preventiva'),
        ('OTRO', 'Otra Actividad / Requerimiento'),
    ]
    
    ESTADO_CHOICES = [
        ('RESUELTO', 'Resuelto / Finalizado'),
        ('EN_PROCESO', 'En Proceso'),
        ('PENDIENTE', 'Pendiente / Abierto'),
    ]
    
    PRIORIDAD_CHOICES = [
        ('NORMAL', 'Normal'),
        ('ALTA', 'Alta'),
        ('URGENTE', 'Urgente'),
    ]
    
    titulo = models.CharField(
        max_length=200,
        verbose_name='Título / Asunto'
    )
    descripcion = models.TextField(
        verbose_name='¿Qué se hizo? (Descripción del trabajo)'
    )
    categoria = models.CharField(
        max_length=40,
        choices=CATEGORIA_CHOICES,
        default='SOPORTE_FUNCIONARIO',
        verbose_name='Categoría de Actividad'
    )
    lugar = models.ForeignKey(
        LugarEquipo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets',
        verbose_name='Lugar / Ubicación'
    )
    lugar_personalizado = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Lugar Personalizado (si no está en lista)'
    )
    funcionario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_atendidos',
        verbose_name='Funcionario Atendido / Solicitante'
    )
    equipo = models.ForeignKey(
        Equipo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_bitacora',
        verbose_name='Equipo Involucrado (Opcional)'
    )
    falla_asociada = models.ForeignKey(
        FallaEquipo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_derivados',
        verbose_name='Falla Reportada Asociada'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='RESUELTO',
        verbose_name='Estado del Ticket'
    )
    prioridad = models.CharField(
        max_length=20,
        choices=PRIORIDAD_CHOICES,
        default='NORMAL',
        verbose_name='Prioridad'
    )
    fecha_actividad = models.DateField(
        verbose_name='Fecha de la Actividad'
    )
    hora_actividad = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora de la Actividad'
    )
    resolucion = models.TextField(
        blank=True,
        verbose_name='Detalle de Resolución / Observaciones Finales'
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='tickets_registrados_bitacora',
        verbose_name='Registrado por'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ticket / Bitácora TI'
        verbose_name_plural = 'Tickets y Bitácora TI'
        ordering = ['-fecha_actividad', '-fecha_creacion']

    def __str__(self):
        func_name = self.funcionario.get_full_name() if self.funcionario else 'General'
        return f"[{self.fecha_actividad}] {self.titulo} - {func_name}"

    @property
    def lugar_display(self):
        if self.lugar:
            return self.lugar.nombre
        return self.lugar_personalizado or 'Sin especificar'

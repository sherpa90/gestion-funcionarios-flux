from django.contrib import admin
from .models import AuditLog, SystemSettings


class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('notifications_status', 'liquidations_status', 'attendance_status', 'updated_at')
    readonly_fields = ('updated_at',)
    
    def notifications_status(self, obj):
        return "Habilitado" if obj.notifications_enabled else "Silenciado"
    notifications_status.short_description = "Notificaciones Generales"
    
    def liquidations_status(self, obj):
        return "Habilitado" if obj.liquidations_notifications_enabled else "Deshabilitado"
    liquidations_status.short_description = "Liquidaciones"
    
    def attendance_status(self, obj):
        return "Habilitado" if obj.attendance_notifications_enabled else "Deshabilitado"
    attendance_status.short_description = "Asistencia"
    
    fieldsets = (
        ('Notificaciones Generales', {
            'fields': ('notifications_enabled',)
        }),
        ('Notificaciones por Tipo', {
            'fields': ('liquidations_notifications_enabled', 'attendance_notifications_enabled')
        }),
        ('Metadatos', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        })
    )
    
    def has_add_permission(self, request):
        return True
    
    def has_change_permission(self, request, obj=None):
        return request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR']
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_view_permission(self, request, obj=None):
        return request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR']


admin.site.register(SystemSettings, SystemSettingsAdmin)
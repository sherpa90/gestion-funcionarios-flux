from django.contrib import admin
from axes.models import AccessAttempt, AccessLog, AccessAxis


@admin.register(AccessAttempt)
class AccessAttemptAdmin(admin.ModelAdmin):
    list_display = ['username', 'ip_address', 'attempt_time', 'user_agent', 'locked']
    list_filter = ['attempt_time', 'locked']
    search_fields = ['username', 'ip_address']
    readonly_fields = ['attempt_time', 'username', 'ip_address', 'user_agent', 'http_accept', 'path_info', 'locked']
    ordering = ['-attempt_time']
    
    actions = ['desbloquear_seleccionados']
    
    def desbloquear_seleccionados(self, request, queryset):
        queryset.delete()
        self.message_user(request, 'Bloqueos seleccionados eliminados')
    desbloquear_seleccionados.short_description = 'Desbloquear seleccionados'


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ['username', 'ip_address', 'attempt_time', 'status']
    list_filter = ['attempt_time', 'status']
    search_fields = ['username', 'ip_address']
    readonly_fields = ['attempt_time', 'username', 'ip_address', 'user_agent', 'status']
    ordering = ['-attempt_time']


@admin.register(AccessAxis)
class AccessAxisAdmin(admin.ModelAdmin):
    list_display = ['username', 'ip_address', 'failures', 'locked']
    list_filter = ['locked']
    search_fields = ['username', 'ip_address']
    readonly_fields = ['username', 'ip_address', 'failures', 'locked', 'last_attempt', 'first_failure']
    
    actions = ['desbloquear_seleccionados']
    
    def desbloquear_seleccionados(self, request, queryset):
        queryset.delete()
        self.message_user(request, 'Usuarios seleccionados desbloqueados')
    desbloquear_seleccionados.short_description = 'Desbloquear seleccionados'

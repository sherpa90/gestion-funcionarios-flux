from django.contrib import admin

# Intentar importar modelos de Axes
try:
    from axes.models import AccessAttempt, AccessLog
    AXES_AVAILABLE = True
except ImportError:
    AXES_AVAILABLE = False


if AXES_AVAILABLE:
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

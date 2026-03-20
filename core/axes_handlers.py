"""
Handler personalizado de Axes para:
1. Excluir administradores del bloqueo
2. Bloqueo por usuario (no por IP)
"""
from axes.handlers.database import AxesDatabaseHandler
from axes.helpers import get_client_ip_address, get_client_username
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminExcludedAxesHandler(AxesDatabaseHandler):
    """
    Handler de Axes que:
    - Excluye a los usuarios staff/admin del bloqueo
    - Usa solo username para el bloqueo (no IP)
    """
    
    def get_failures(self, request, credentials=None):
        """
        Obtiene los intentos fallidos SOLO por username, no por IP.
        """
        username = get_client_username(request) or (credentials.get('username') if credentials else None)
        
        # Si es un administrador, no contar fallos
        if username:
            try:
                user = User.objects.filter(email=username).first()
                if user and (user.is_staff or user.is_superuser):
                    return []
            except Exception:
                pass
        
        # Usar solo username para el conteo de fallos
        from axes.models import AccessAttempt
        
        # Filtrar solo por username, ignorar IP
        attempts = AccessAttempt.objects.filter(
            username=username
        ).order_by('-attempt_time')
        
        return list(attempts)
    
    def is_locked(self, request, credentials=None):
        """
        Verifica si el usuario está bloqueado (solo por username).
        """
        username = get_client_username(request) or (credentials.get('username') if credentials else None)
        
        # Los administradores nunca se bloquean
        if username:
            try:
                user = User.objects.filter(email=username).first()
                if user and (user.is_staff or user.is_superuser):
                    return False
            except Exception:
                pass
        
        # Verificar bloqueo solo por username
        from axes.models import AccessAttempt
        from django.utils import timezone
        
        failures = self.get_failures(request, credentials)
        
        if not failures:
            return False
        
        # Verificar si está dentro del período de bloqueo
        from datetime import timedelta
        from django.conf import settings
        
        cooloff_time = getattr(settings, 'AXES_COOLOFF_TIME', timedelta(hours=1))
        cutoff = timezone.now() - cooloff_time
        
        # Contar fallos recientes
        recent_failures = [f for f in failures if f.attempt_time > cutoff]
        
        if len(recent_failures) >= getattr(settings, 'AXES_FAILURE_LIMIT', 8):
            return True
        
        return False
    
    def lockout_response(self, request):
        """
        Respuesta cuando usuario está bloqueado.
        """
        from django.http import HttpResponseForbidden
        from django.template import loader
        from django.conf import settings
        
        # Intentar cargar template personalizado
        try:
            template = loader.get_template(getattr(settings, 'AXES_LOCKOUT_TEMPLATE', 'account/locked.html'))
            return HttpResponseForbidden(template.render({}, request))
        except Exception:
            return HttpResponseForbidden('Tu cuenta está temporalmente bloqueada. Intenta más tarde.')
    
    def handle_already_locked(self, request, credentials):
        """
        Manejo cuando ya está bloqueado.
        """
        # Permitir si es administrador
        username = get_client_username(request) or (credentials.get('username') if credentials else None)
        if username:
            try:
                user = User.objects.filter(email=username).first()
                if user and (user.is_staff or user.is_superuser):
                    return None  # Permitir acceso
            except Exception:
                pass
        
        return super().handle_already_locked(request, credentials)
    
    def handle_lockout(self, request, credentials):
        """
        Manejo del bloqueo.
        """
        # Permitir si es administrador
        username = get_client_username(request) or (credentials.get('username') if credentials else None)
        if username:
            try:
                user = User.objects.filter(email=username).first()
                if user and (user.is_staff or user.is_superuser):
                    return None  # No aplicar bloqueo
            except Exception:
                pass
        
        return super().handle_lockout(request, credentials)

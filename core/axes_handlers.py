"""
Handler personalizado de Axes para:
1. Excluir administradores del bloqueo
2. Bloqueo por usuario (no por IP)
"""
from axes.handlers.database import AxesDatabaseHandler
from axes.helpers import get_client_username
from django.contrib.auth import get_user_model

User = get_user_model()


def _is_admin_user(username):
    """Retorna True si el username corresponde a un usuario staff/superuser."""
    if not username:
        return False
    try:
        # Buscamos por email ya que es el USERNAME_FIELD
        user = User.objects.filter(email=username).first()
        return bool(user and (user.is_staff or user.is_superuser))
    except Exception:
        return False


class AdminExcludedAxesHandler(AxesDatabaseHandler):
    """
    Handler de Axes que:
    - Excluye a los usuarios staff/admin del bloqueo
    - Delega el resto al handler base (AxesDatabaseHandler)
    """

    def user_login_failed(self, sender, request, credentials, **kwargs):
        """
        Registra un intento fallido. Si el usuario es admin, no registra nada.
        """
        username = get_client_username(request) or (credentials.get('username') if credentials else None)
        
        if _is_admin_user(username):
            return  # No registrar fallos para administradores
            
        return super().user_login_failed(sender, request, credentials, **kwargs)

    def is_locked(self, request, credentials=None):
        """
        Verifica si el usuario está bloqueado. Los administradores nunca se bloquean.
        """
        username = get_client_username(request) or (credentials.get('username') if credentials else None)
        
        if _is_admin_user(username):
            return False  # Los admins nunca se bloquean
            
        return super().is_locked(request, credentials)

    def handle_already_locked(self, request, credentials):
        """
        Manejo cuando ya está bloqueado. Permitir si es administrador.
        """
        username = get_client_username(request) or (credentials.get('username') if credentials else None)
        
        if _is_admin_user(username):
            return None  # Permitir acceso
            
        return super().handle_already_locked(request, credentials)

    def handle_lockout(self, request, credentials):
        """
        Manejo del bloqueo. No aplicar a administradores.
        """
        username = get_client_username(request) or (credentials.get('username') if credentials else None)
        
        if _is_admin_user(username):
            return None  # No aplicar bloqueo
            
        return super().handle_lockout(request, credentials)

"""
Handler personalizado de Axes para:
1. Excluir administradores del bloqueo
2. Bloqueo por usuario (no por IP)
"""
from axes.handlers.database import AxesDatabaseHandler
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminExcludedAxesHandler(AxesDatabaseHandler):
    """
    Handler de Axes que:
    - Excluye a los usuarios staff/admin del bloqueo
    - Usa solo username para el bloqueo (no IP)
    """
    
    def _get_username_from_request(self, request):
        """
        Extrae el username/email del request de manera segura.
        """
        # Verificar si request es válido y tiene los atributos necesarios
        if not request or not hasattr(request, 'POST'):
            return None

        # Intentar obtener el email del formulario POST
        try:
            if request.POST:
                return request.POST.get('username') or request.POST.get('email')
            
            # Para requests de API o si se usa django-rest-framework
            if hasattr(request, 'data') and isinstance(request.data, dict):
                return request.data.get('username') or request.data.get('email')
        except Exception:
            pass
        
        # Intentar obtener de axes como último recurso
        try:
            from axes.helpers import get_client_username
            return get_client_username(request)
        except Exception:
            pass
        
        return None
    
    def _is_admin_user(self, username):
        """
        Verifica si el usuario es administrador.
        """
        if not username:
            return False
        try:
            user = User.objects.filter(email=username).first()
            if user and (user.is_staff or user.is_superuser):
                return True
        except Exception:
            pass
        return False
    
    def get_failures(self, request, credentials=None):
        """
        Obtiene los intentos fallidos SOLO por username, no por IP.
        """
        username = self._get_username_from_request(request)
        if credentials:
            username = username or credentials.get('username') or credentials.get('email')
        
        # Si es un administrador, no contar fallos
        if username and self._is_admin_user(username):
            return []
        
        # Usar el método original del padre
        return super().get_failures(request, credentials)
    
    def is_locked(self, request, credentials=None):
        """
        Verifica si el usuario está bloqueado (solo por username).
        """
        username = self._get_username_from_request(request)
        if credentials:
            username = username or credentials.get('username') or credentials.get('email')
        
        # Los administradores nunca se bloquean
        if username and self._is_admin_user(username):
            return False
        
        # Usar el método original del padre
        return super().is_locked(request, credentials)
    
    def user_login_failed(self, *args, **kwargs):
        """
        Maneja el evento de login fallido de forma flexible para evitar TypeErrors.
        """
        # Extraer request y credentials de args o kwargs
        # En señales de Django: (sender, credentials, **kwargs)
        # Axes puede pasar: (request, credentials) o (sender, credentials, request)
        
        request = kwargs.get('request')
        credentials = kwargs.get('credentials')
        
        # Si vienen posicionales (típico en proxies de Axes)
        if not request and len(args) >= 1:
            # Podría ser (request, credentials) o (sender, credentials, request)
            # Intentamos detectar si el primer arg es un request
            if hasattr(args[0], 'META') or hasattr(args[0], 'POST'):
                request = args[0]
            
        if not credentials:
            if len(args) >= 2:
                # Si (request, credentials) -> args[1]
                # Si (sender, credentials) -> args[1]
                credentials = args[1]
            elif isinstance(args[0], dict) and not request:
                # Si solo se pasó un dict y no detectamos request -> probablemente credentials
                credentials = args[0]
        
        # Intentar obtener username/email
        username = self._get_username_from_request(request) if request else None
        if credentials:
            username = username or credentials.get('username') or credentials.get('email')
        
        # Si es administrador, no registrar el fallo en Axes (evitar bloqueo)
        if username and self._is_admin_user(username):
            return
        
        # Usar el método original
        super().user_login_failed(*args, **kwargs)
    
    def user_login_success(self, *args, **kwargs):
        """
        Maneja el evento de login exitoso de forma flexible.
        """
        # En Django exitoso: (sender, user, **kwargs) donde request está en kwargs
        # En Axes: (request, user)
        
        user = kwargs.get('user')
        if not user and len(args) >= 2:
            # Podría ser (sender, user) o (request, user)
            user = args[1]
            
        # Si es administrador, no registrar el éxito (para no resetear contadores de fallos fallidos)
        if hasattr(user, 'is_staff') and user.is_staff:
            return
        
        # Usar el método original
        super().user_login_success(*args, **kwargs)

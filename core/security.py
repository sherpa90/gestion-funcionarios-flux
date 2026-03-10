"""
Security middleware and utilities for SGPAL.
Addresses OWASP Top 10 — A05 Security Misconfiguration.
"""
import logging
import time
from django.conf import settings

logger = logging.getLogger('security')
audit_logger = logging.getLogger('audit')


# ─────────────────────────────────────────────
# A05 — Security Headers Middleware
# ─────────────────────────────────────────────

class SecurityHeadersMiddleware:
    """
    Agrega headers de seguridad HTTP a todas las respuestas.
    OWASP A05: Security Misconfiguration
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Prevenir MIME type sniffing (A05)
        response['X-Content-Type-Options'] = 'nosniff'

        # Prevenir clickjacking (A05)
        response['X-Frame-Options'] = 'DENY'

        # Controlar información de referrer (A02)
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Deshabilitar características del navegador no utilizadas (A05)
        response['Permissions-Policy'] = (
            'accelerometer=(), '
            'camera=(), '
            'geolocation=(), '
            'gyroscope=(), '
            'magnetometer=(), '
            'microphone=(), '
            'payment=(), '
            'usb=()'
        )

        # Prevenir cache de respuestas sensibles en sesiones autenticadas
        if request.user.is_authenticated if hasattr(request, 'user') else False:
            if not response.has_header('Cache-Control'):
                response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
                response['Pragma'] = 'no-cache'

        return response


# ─────────────────────────────────────────────
# A09 — Audit Logging
# ─────────────────────────────────────────────

def get_client_ip(request):
    """Extrae la IP real considerando proxies reversos."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Tomar la primera IP (la del cliente original)
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    return ip


def audit_log(request, action: str, details: str = '', success: bool = True):
    """
    Registra acciones sensibles con contexto de seguridad completo.
    OWASP A09: Security Logging and Monitoring Failures

    Args:
        request: HttpRequest actual
        action: Nombre de la acción (ej: 'USER_CREATED', 'PASSWORD_CHANGED')
        details: Detalles adicionales de la acción
        success: Si la acción fue exitosa
    """
    user_id = getattr(request.user, 'pk', None) if hasattr(request, 'user') else None
    username = getattr(request.user, 'email', 'anonymous') if hasattr(request, 'user') else 'anonymous'
    ip = get_client_ip(request)

    status = 'SUCCESS' if success else 'FAILURE'

    audit_logger.info(
        f'[AUDIT] {status} | action={action} | user_id={user_id} | '
        f'email={username} | ip={ip} | details={details}'
    )

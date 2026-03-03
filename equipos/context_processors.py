import logging
from .models import FallaEquipo

logger = logging.getLogger(__name__)

def pending_failures_count(request):
    """Provee la cantidad de fallas reportadas pendientes para mostrar en notificaciones"""
    logger.debug(f"[CONTEXT PROCESSOR] pending_failures_count called - user: {request.user}, authenticated: {request.user.is_authenticated if hasattr(request.user, 'is_authenticated') else 'N/A'}")
    
    # Verificar si el usuario tiene el atributo role
    if not hasattr(request.user, 'role'):
        logger.warning(f"[CONTEXT PROCESSOR] User {request.user} does not have 'role' attribute")
        return {'pending_failures_count': 0}
    
    if request.user.is_authenticated and request.user.role in ('ADMIN', 'SECRETARIA'):
        try:
            count = FallaEquipo.objects.filter(estado='REPORTADA').count()
            logger.debug(f"[CONTEXT PROCESSOR] Found {count} pending failures")
            return {'pending_failures_count': count}
        except Exception as e:
            logger.error(f"[CONTEXT PROCESSOR] Error getting pending failures: {e}")
            return {'pending_failures_count': 0}
    logger.debug("[CONTEXT PROCESSOR] User not authenticated or not ADMIN/SECRETARIA, returning 0")
    return {'pending_failures_count': 0}

from .models import FallaEquipo


def pending_failures_count(request):
    """Provee la cantidad de fallas reportadas pendientes para mostrar en notificaciones"""
    if not hasattr(request.user, 'is_authenticated') or not request.user.is_authenticated:
        return {'pending_failures_count': 0}

    if not hasattr(request.user, 'role'):
        return {'pending_failures_count': 0}

    if request.user.role in ('ADMIN', 'SECRETARIA'):
        try:
            count = FallaEquipo.objects.filter(estado='REPORTADA').count()
            return {'pending_failures_count': count}
        except Exception:
            return {'pending_failures_count': 0}

    return {'pending_failures_count': 0}

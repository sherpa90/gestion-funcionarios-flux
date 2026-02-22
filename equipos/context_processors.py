from .models import FallaEquipo

def pending_failures_count(request):
    """Provee la cantidad de fallas reportadas pendientes para mostrar en notificaciones"""
    if request.user.is_authenticated and request.user.role in ('ADMIN', 'SECRETARIA'):
        try:
            count = FallaEquipo.objects.filter(estado='REPORTADA').count()
            return {'pending_failures_count': count}
        except Exception:
            return {'pending_failures_count': 0}
    return {'pending_failures_count': 0}

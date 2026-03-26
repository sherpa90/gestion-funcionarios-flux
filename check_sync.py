from users.models import CustomUser
from permisos.models import SolicitudPermiso
from django.db.models import Sum

for u in CustomUser.objects.all():
    aprobados = SolicitudPermiso.objects.filter(usuario=u, estado='APROBADO').aggregate(s=Sum('dias_solicitados'))['s'] or 0
    teorico = max(0, 6.0 - aprobados)
    if abs(u.dias_disponibles - teorico) > 0.01:
        print(f"SYNC_ERROR: {u.get_full_name()} ({u.run}) -> Actual: {u.dias_disponibles}, Teorico: {teorico}")

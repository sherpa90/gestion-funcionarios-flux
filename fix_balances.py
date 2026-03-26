import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import CustomUser
from permisos.models import SolicitudPermiso
from django.db.models import Sum

def sync_all_balances():
    users = CustomUser.objects.all()
    count = 0
    for user in users:
        # Sumar todos los días de permisos APROBADOS del año actual (o total si no hay reseteo anual implementado aún)
        # Por ahora asumiremos total histórico según la lógica actual del sistema
        aprobados = SolicitudPermiso.objects.filter(usuario=user, estado='APROBADO').aggregate(total=Sum('dias_solicitados'))['total'] or 0.0
        
        balance_teorico = max(0.0, 6.0 - aprobados)
        
        if abs(user.dias_disponibles - balance_teorico) > 0.01:
            print(f"Usuario {user.get_full_name()} ({user.run}): Balance actual {user.dias_disponibles}, Teórico {balance_teorico}. CORRIGIENDO...")
            user.dias_disponibles = balance_teorico
            user.save()
            count += 1
            
    print(f"Proceso terminado. Se corrigieron {count} usuarios.")

if __name__ == "__main__":
    sync_all_balances()

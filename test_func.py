import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from permisos.forms import SolicitudBypassForm
from users.models import CustomUser

admin = CustomUser.objects.filter(role='ADMIN').first()
target = CustomUser.objects.filter(role='FUNCIONARIO').first()

form = SolicitudBypassForm({
    'usuario': target.id,
    'fecha_inicio': '2026-03-20',
    'dias_solicitados': '1.0',
    'jornada': '',
    'observacion': 'Test'
})

if form.is_valid():
    print("Form is valid")
    try:
        from core.services import BusinessDayCalculator
        from django.db.models import Sum
        form.instance.fecha_termino = BusinessDayCalculator.calculate_end_date(
            form.instance.fecha_inicio, 
            form.instance.dias_solicitados
        )
        print("End date calculated:", form.instance.fecha_termino)
        
        usuario = form.instance.usuario
        from permisos.models import SolicitudPermiso
        solicitudes_pendientes = SolicitudPermiso.objects.filter(
            usuario=usuario,
            estado='PENDIENTE'
        ).aggregate(total=Sum('dias_solicitados'))['total'] or 0.0
        print("Pendientes:", solicitudes_pendientes)
        
        form.instance.estado = 'PENDIENTE'
        form.instance.created_by = admin
        
        form.save()
        print("Saved successfully")
    except Exception as e:
        import traceback
        traceback.print_exc()
else:
    print("Form errors:", form.errors)

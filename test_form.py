import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from permisos.forms import SolicitudAdminForm
from permisos.models import SolicitudPermiso

# Obtener un permiso real
obj = SolicitudPermiso.objects.last()

# Simular POST data con todos los campos requeridos
data = {
    'fecha_inicio': str(obj.fecha_inicio),
    'dias_solicitados': str(obj.dias_solicitados),
    'jornada': obj.jornada,
    'observacion': 'test',
    'estado': 'APROBADO',
}

f = SolicitudAdminForm(data=data, instance=obj)
is_valid = f.is_valid()
print("Form is valid:", is_valid)
if not is_valid:
    print("Errors:", f.errors)
else:
    print("Cleaned data keys:", list(f.cleaned_data.keys()))
    print("Cleaned estado:", f.cleaned_data.get('estado'))

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def run():
    from permisos.forms import SolicitudAdminForm
    from permisos.models import SolicitudPermiso

    obj = SolicitudPermiso.objects.last()
    if not obj:
        print("No SolicitudPermiso found in DB.")
        return

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

if __name__ == '__main__':
    run()

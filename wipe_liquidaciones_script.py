import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from liquidaciones.models import Liquidacion

count = 0
try:
    liquidaciones = Liquidacion.objects.all()
    total = liquidaciones.count()
    for liq in liquidaciones:
        if liq.archivo:
            liq.archivo.delete(save=False)
        liq.delete()
        count += 1
    print(f"Éxito. Se eliminaron {count} de {total} liquidaciones correctamente y sus archivos físicos asociados.")
except Exception as e:
    print(f"Error: {e}")

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from users.models import CustomUser

client = Client()
admin = CustomUser.objects.filter(role='ADMIN').first()
client.force_login(admin)

user_target = CustomUser.objects.filter(role='FUNCIONARIO').first()

try:
    response = client.post('/permisos/ingresar-directo/', {
        'usuario': user_target.id,
        'fecha_inicio': '2026-03-20',
        'dias_solicitados': '1.0',
        'jornada': '',
        'observacion': ''
    })
    print(f"Status Code: {response.status_code}")
except Exception as e:
    import traceback
    traceback.print_exc()

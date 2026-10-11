import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def run():
    from django.test import Client
    from users.models import CustomUser

    client = Client()
    admin = CustomUser.objects.filter(role='ADMIN').first()
    if not admin:
        print("No admin user found.")
        return
    client.force_login(admin)

    user_target = CustomUser.objects.filter(role='FUNCIONARIO').first()
    if not user_target:
        print("No funcionario user found.")
        return

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

if __name__ == '__main__':
    run()

#!/usr/bin/env python
import os
import django
from django.conf import settings

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import CustomUser

# Crear superusuario
try:
    user = CustomUser(
        email='admin@example.com',
        run='11111111-1',
        first_name='Admin',
        last_name='User',
        is_superuser=True,
        is_staff=True,
        role='ADMIN'
    )
    user.set_password('admin123')
    user.save()
    print("Superusuario creado exitosamente.")
except Exception as e:
    print(f"Error creando superusuario: {e}")
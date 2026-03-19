#!/usr/bin/env python3
"""Script de emergencia para recrear el usuario administrador"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

run = '17.639.211-8'
email = 'mrosas@losalercespuertomontt.cl'
password = 'Mrosas12345!'

try:
    user = User.objects.get(email=email)
    user.set_password(password)
    user.role = 'ADMIN'
    user.is_active = True
    user.is_blocked = False
    user.save()
    print(f"✅ Usuario '{email}' actualizado con contraseña nueva.")
except User.DoesNotExist:
    user = User.objects.create_user(
        username=run,
        email=email,
        password=password,
        run=run,
        first_name='Marco',
        last_name='Rosas',
        role='ADMIN',
        is_active=True,
        is_blocked=False,
    )
    print(f"✅ Usuario administrador recreado: {email} / {password}")
except Exception as e:
    print(f"❌ Error: {e}")

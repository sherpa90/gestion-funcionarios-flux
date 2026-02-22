#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/app')

django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()
users = User.objects.all().values('id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff')
for u in users:
    print(f"ID: {u['id']} | {u['username']} | {u['email']} | {u['first_name']} {u['last_name']} | Activo: {u['is_active']} | Admin: {u['is_staff']}")

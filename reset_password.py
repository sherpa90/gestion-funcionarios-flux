#!/usr/bin/env python
import os
import sys
import django
import random
import string

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/app')

django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Reset password for user ID 1
user = User.objects.get(id=1)
new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
user.set_password(new_password)
user.save()

print(f"Usuario: {user.username}")
print(f"Nueva contraseña: {new_password}")

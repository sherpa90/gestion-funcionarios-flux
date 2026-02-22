#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/app')

django.setup()

# Try to delete all Access attempts
try:
    from axes.models import AccessAttempt
    count = AccessAttempt.objects.all().count()
    AccessAttempt.objects.all().delete()
    print(f"Se eliminaron {count} intentos de acceso")
except Exception as e:
    print(f"Error: {e}")

# Try to delete all AccessLog
try:
    from axes.models import AccessLog
    count = AccessLog.objects.all().count()
    AccessLog.objects.all().delete()
    print(f"Se eliminaron {count} registros de acceso")
except Exception as e:
    print(f"Error: {e}")

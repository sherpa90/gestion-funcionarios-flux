#!/usr/bin/env python
"""
Servidor de desarrollo Django con soporte HTTPS para localhost.
Uso: python runserver_https.py [puerto]
"""
import os
import sys
import ssl
import pathlib

# Agregar el proyecto al path
sys.path.insert(0, str(pathlib.Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.core.management import call_command

# Ejecutar runserver con SSL
if __name__ == '__main__':
    port = sys.argv[1] if len(sys.argv) > 1 else '8000'
    call_command('runserver', f'0.0.0.0:{port}', use_reloader=False)
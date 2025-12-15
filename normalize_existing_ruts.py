#!/usr/bin/env python3
"""
Script para normalizar todos los RUTs existentes en la base de datos al formato chileno con puntos.
Ejecutar con: python manage.py shell -c "exec(open('normalize_existing_ruts.py').read())"
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/home/sherpa90/Documentos/sgpal')
django.setup()

from users.models import CustomUser
from core.utils import normalize_rut

def normalize_existing_ruts():
    """Normaliza todos los RUTs existentes al formato chileno con puntos"""
    print("🔄 Normalizando RUTs existentes en la base de datos...")
    print("=" * 60)

    usuarios_actualizados = 0
    usuarios_procesados = 0

    # Mostrar estado inicial
    print("📊 Estado inicial de RUTs:")
    for user in CustomUser.objects.all()[:10]:  # Mostrar primeros 10
        print(f"  {user.run} - {user.get_full_name()}")
    print()

    # Normalizar todos los RUTs al formato chileno con puntos
    for user in CustomUser.objects.all():
        usuarios_procesados += 1
        rut_original = user.run
        rut_normalizado = normalize_rut(rut_original)

        if rut_original != rut_normalizado:
            print(f"🔄 Normalizando: {user.get_full_name()}")
            print(f"   {rut_original} → {rut_normalizado}")
            user.run = rut_normalizado
            user.save(update_fields=['run'])
            usuarios_actualizados += 1
            print("   ✅ Actualizado\n")

    print("📊 Estado final de RUTs:")
    for user in CustomUser.objects.all()[:10]:  # Mostrar primeros 10
        print(f"  {user.run} - {user.get_full_name()}")
    print()

    print("🎉 Normalización completada!")
    print(f"   • Usuarios procesados: {usuarios_procesados}")
    print(f"   • Usuarios actualizados: {usuarios_actualizados}")
    print(f"   • Usuarios ya normalizados: {usuarios_procesados - usuarios_actualizados}")

if __name__ == '__main__':
    normalize_existing_ruts()
#!/usr/bin/env python3
"""
Script para verificar los RUTs en la base de datos y su formato.
Ejecutar con: python manage.py shell -c "exec(open('check_ruts.py').read())"
"""

from users.models import CustomUser
from core.utils import normalize_rut

print("🔍 Verificación de RUTs en la base de datos")
print("=" * 50)

total_users = CustomUser.objects.count()
print(f"Total de usuarios: {total_users}")

print("\n📋 Primeros 20 usuarios con sus RUTs:")
print("-" * 50)
for i, user in enumerate(CustomUser.objects.all()[:20], 1):
    rut_formateado = normalize_rut(user.run)
    print("2d")

print("\n🔎 Análisis de formatos de RUT:")
print("-" * 50)

# Contar diferentes formatos
formatos = {}
for user in CustomUser.objects.all():
    rut = user.run
    if '.' in rut and '-' in rut:
        formato = "completo (con puntos y guión)"
    elif '.' in rut:
        formato = "con puntos"
    elif '-' in rut:
        formato = "con guión"
    else:
        formato = "simple (solo números)"

    formatos[formato] = formatos.get(formato, 0) + 1

for formato, count in formatos.items():
    print(f"  {formato}: {count} usuarios")

print("\n✅ Función normalize_rut aplicada a algunos ejemplos:")
print("-" * 50)
ejemplos = ["9479036-0", "17.639.211-8", "176392118", "12.345.678-K"]
for ejemplo in ejemplos:
    formateado = normalize_rut(ejemplo)
    print(f"  '{ejemplo}' -> '{formateado}'")

print("\n💡 Para ver más usuarios, ejecuta:")
print("   CustomUser.objects.all()[:50]  # Para ver los primeros 50")
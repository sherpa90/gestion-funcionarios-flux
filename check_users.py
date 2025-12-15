#!/usr/bin/env python
"""
Script para verificar qué usuarios existen en la base de datos
y comparar con los RUTs del archivo Excel.
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import CustomUser

def main():
    print("🔍 Verificando usuarios en la base de datos...")
    print("=" * 60)

    # Obtener todos los usuarios
    users = CustomUser.objects.all().order_by('run')

    print(f"📊 Total de usuarios en BD: {users.count()}")
    print()

    # Mostrar primeros 20 usuarios
    print("👥 Primeros 20 usuarios:")
    print("-" * 40)
    for i, user in enumerate(users[:20], 1):
        print("2d")
    print()

    # Mostrar RUTs únicos
    runs = list(users.values_list('run', flat=True))
    print(f"🏷️  RUTs únicos en BD ({len(runs)}):")
    print("-" * 40)
    for run in sorted(runs):
        print(f"  {run}")
    print()

    # Verificar si hay usuarios con RUTs del Excel
    excel_ruts = [
        '9479036-0', '10677028-K', '11218216-0', '11691920-6', '11852851-4',
        '12307885-3', '12309374-7', '12492340-9', '13121589-4', '13738844-8',
        '14085333-K', '14097697-0', '14237121-9', '15285103-0', '15287150-3',
        '15303738-8', '15639556-0', '16112553-9', '16316441-8', '16453262-3',
        '16507789-K', '16650250-0', '16722808-9', '17037591-2', '17538272-0',
        '17639211-8', '17810590-6', '17890098-6', '17957359-8', '18578438-K',
        '18733765-8', '18734451-4', '18753368-6', '18902090-2', '18963373-4',
        '19366026-6', '19540660-K', '19759241-9', '20031978-8', '20064974-5',
        '20293727-6', '20983875-3', '21507470-6', '21557023-1'
    ]

    print("🔍 Comparando con RUTs del Excel:")
    print("-" * 40)

    encontrados = []
    no_encontrados = []

    for rut_excel in excel_ruts:
        # Buscar usuario con este RUT
        user = None
        try:
            user = CustomUser.objects.get(run=rut_excel)
        except CustomUser.DoesNotExist:
            # Intentar con variaciones
            for run_bd in runs:
                if run_bd.replace('.', '').replace('-', '') == rut_excel.replace('-', ''):
                    user = CustomUser.objects.get(run=run_bd)
                    break

        if user:
            encontrados.append((rut_excel, user.run, user.get_full_name()))
        else:
            no_encontrados.append(rut_excel)

    print(f"✅ RUTs encontrados ({len(encontrados)}):")
    for rut_excel, rut_bd, nombre in encontrados:
        print(f"  {rut_excel} → {rut_bd} ({nombre})")

    print()
    print(f"❌ RUTs NO encontrados ({len(no_encontrados)}):")
    for rut in no_encontrados[:10]:  # Mostrar primeros 10
        print(f"  {rut}")
    if len(no_encontrados) > 10:
        print(f"  ... y {len(no_encontrados) - 10} más")

    print()
    print("💡 Recomendaciones:")
    if len(encontrados) == 0:
        print("  - No hay usuarios en la base de datos")
        print("  - Necesitas crear usuarios primero")
    elif len(no_encontrados) > 0:
        print("  - Algunos RUTs no coinciden exactamente")
        print("  - Verifica el formato de los RUTs en la BD")
        print("  - La función find_user_by_rut debería manejar variaciones")

if __name__ == '__main__':
    main()
#!/usr/bin/env python
"""
Script para extraer todos los RUTs del archivo Excel y compararlos con la BD
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import CustomUser
from core.utils import normalize_rut

def extract_ruts_from_excel():
    """Extrae todos los RUTs únicos del archivo Excel"""
    excel_file = 'templates/Asistentes_Nov.xlsx'

    if not os.path.exists(excel_file):
        print(f"❌ Archivo no encontrado: {excel_file}")
        return set()

    try:
        import openpyxl
        wb = openpyxl.load_workbook(excel_file, data_only=True)
        ws = wb.active

        ruts_excel = set()
        for row in ws.iter_rows(min_row=2, values_only=True):  # Skip header
            if row and len(row) >= 1:
                rut_raw = str(row[0]).strip() if row[0] else None
                if rut_raw:
                    ruts_excel.add(rut_raw)

        print(f"📄 Extraídos {len(ruts_excel)} RUTs únicos del Excel")
        return ruts_excel

    except Exception as e:
        print(f"❌ Error leyendo Excel: {e}")
        return set()

def find_user_by_rut(rut_encontrado: str):
    """
    Busca un usuario por RUT con matching inteligente
    """
    try:
        # Limpiar el RUT encontrado
        rut_limpio = rut_encontrado.upper().replace(' ', '').strip()

        # Crear diferentes variaciones para buscar
        variaciones_rut = set()
        variaciones_rut.add(rut_limpio)

        # RUT normalizado
        rut_normalizado = normalize_rut(rut_encontrado)
        variaciones_rut.add(rut_normalizado)

        # RUT sin puntos
        rut_sin_puntos = rut_normalizado.replace('.', '')
        variaciones_rut.add(rut_sin_puntos)

        # Si tiene puntos, intentar sin ellos
        if '.' in rut_limpio:
            variaciones_rut.add(rut_limpio.replace('.', ''))

        # Si no tiene puntos pero tiene guión, intentar con puntos
        if '.' not in rut_limpio and '-' in rut_limpio:
            parts = rut_limpio.split('-')
            if len(parts) == 2:
                cuerpo, dv = parts
                cuerpo = cuerpo.replace('.', '')

                if len(cuerpo) == 8:
                    cuerpo_con_puntos = f"{cuerpo[:2]}.{cuerpo[2:5]}.{cuerpo[5:]}"
                    variaciones_rut.add(f"{cuerpo_con_puntos}-{dv}")
                elif len(cuerpo) == 7:
                    cuerpo_con_puntos = f"{cuerpo[:1]}.{cuerpo[1:4]}.{cuerpo[4:]}"
                    variaciones_rut.add(f"{cuerpo_con_puntos}-{dv}")

        # Intentar cada variación
        for rut_variacion in variaciones_rut:
            try:
                user = CustomUser.objects.get(run=rut_variacion)
                return user, rut_variacion
            except CustomUser.DoesNotExist:
                continue

        return None, None

    except Exception as e:
        print(f"Error finding user by RUT {rut_encontrado}: {e}")
        return None, None

def main():
    print("🔍 Comparando TODOS los RUTs del Excel con la base de datos...")
    print("=" * 80)

    # Extraer RUTs del Excel
    ruts_excel = extract_ruts_from_excel()
    if not ruts_excel:
        return

    print(f"\n📊 RUTs en Excel: {len(ruts_excel)}")
    print("📋 Primeros 10 RUTs del Excel:")
    for i, rut in enumerate(sorted(list(ruts_excel))[:10], 1):
        print("2d")
    print("    ...")

    # Obtener usuarios de BD
    users_bd = {user.run: user for user in CustomUser.objects.all()}
    print(f"\n👥 Usuarios en BD: {len(users_bd)}")

    if users_bd:
        print("📋 Primeros 10 RUTs en BD:")
        for i, rut in enumerate(sorted(list(users_bd.keys()))[:10], 1):
            user = users_bd[rut]
            print("2d")
        print("    ...")
    else:
        print("❌ No hay usuarios en la base de datos!")

    # Comparar
    print(f"\n🔍 Comparación:")
    print("-" * 80)

    encontrados = []
    no_encontrados = []

    for rut_excel in sorted(ruts_excel):
        user, rut_encontrado = find_user_by_rut(rut_excel)

        if user:
            encontrados.append((rut_excel, rut_encontrado, user.get_full_name()))
        else:
            no_encontrados.append(rut_excel)

    print(f"✅ RUTs ENCONTRADOS ({len(encontrados)}):")
    print("-" * 60)
    if encontrados:
        for rut_excel, rut_bd, nombre in encontrados[:20]:  # Mostrar primeros 20
            print("18")
        if len(encontrados) > 20:
            print(f"    ... y {len(encontrados) - 20} más")
    else:
        print("    Ninguno encontrado")

    print(f"\n❌ RUTs NO ENCONTRADOS ({len(no_encontrados)}):")
    print("-" * 60)
    if no_encontrados:
        for rut in no_encontrados[:20]:  # Mostrar primeros 20
            print(f"    {rut}")
        if len(no_encontrados) > 20:
            print(f"    ... y {len(no_encontrados) - 20} más")
    else:
        print("    Todos encontrados!")

    print(f"\n📈 Resumen:")
    print(f"   Excel: {len(ruts_excel)} RUTs únicos")
    print(f"   BD: {len(users_bd)} usuarios")
    print(f"   Encontrados: {len(encontrados)}")
    print(f"   No encontrados: {len(no_encontrados)}")
    print(".1f")

    if len(encontrados) == 0:
        print(f"\n💡 Problema: No hay coincidencias entre Excel y BD")
        print(f"   - Revisa si hay usuarios creados en el sistema")
        print(f"   - Verifica el formato de los RUTs")
    elif len(no_encontrados) > 0:
        print(f"\n💡 Algunos RUTs no coinciden:")
        print(f"   - Posiblemente formato diferente")
        print(f"   - O usuarios faltantes en BD")

if __name__ == '__main__':
    main()
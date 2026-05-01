#!/usr/bin/env python
"""
Script para importar usuarios desde el archivo Excel de asistencia
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import CustomUser
from asistencia.models import HorarioFuncionario
import openpyxl
from datetime import time

def extract_unique_users_from_excel():
    """Extrae usuarios únicos del Excel"""
    excel_file = 'templates/Asistentes_Nov.xlsx'

    if not os.path.exists(excel_file):
        print("Archivo no encontrado: {}".format(excel_file))
        return {}

    try:
        wb = openpyxl.load_workbook(excel_file, data_only=True)
        ws = wb.active

        users_data = {}

        for row in ws.iter_rows(min_row=2, values_only=True):  # Skip header
            if row and len(row) >= 2:
                rut_raw = str(row[0]).strip() if row[0] else None
                nombre_raw = str(row[1]).strip() if row[1] else None

                if rut_raw and nombre_raw:
                    # Limpiar RUT
                    rut = rut_raw.replace('.', '').replace('-', '').strip()

                    # Parsear nombre
                    nombre_parts = nombre_raw.split()
                    if len(nombre_parts) >= 2:
                        first_name = ' '.join(nombre_parts[:-1])
                        last_name = nombre_parts[-1]
                    else:
                        first_name = nombre_raw
                        last_name = ''

                    users_data[rut] = {
                        'rut_display': rut_raw,
                        'first_name': first_name,
                        'last_name': last_name,
                        'full_name': nombre_raw
                    }

        print("Extraidos {} usuarios unicos del Excel".format(len(users_data)))
        return users_data

    except Exception as e:
        print("Error leyendo Excel: {}".format(e))
        return {}

def create_users_and_schedules(users_data):
    """Crea usuarios y horarios por defecto"""
    created_users = 0
    created_schedules = 0
    errors = []

    for rut_clean, user_data in users_data.items():
        try:
            # Verificar si usuario ya existe
            existing_user = CustomUser.objects.filter(run__icontains=rut_clean).first()
            if existing_user:
                print("Usuario ya existe: {} ({})".format(existing_user.get_full_name(), existing_user.run))
                continue

            # Crear usuario
            username = "user_{}".format(rut_clean)

            # Verificar username único
            counter = 1
            original_username = username
            while CustomUser.objects.filter(username=username).exists():
                username = "{}_{}".format(original_username, counter)
                counter += 1

            user = CustomUser.objects.create_user(
                username=username,
                email="{}@empresa.cl".format(username),
                password="123456",  # Contraseña temporal
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                run=user_data['rut_display'],  # Guardar con formato original
                role='FUNCIONARIO'
            )

            print("Usuario creado: {} ({})".format(user.get_full_name(), user.run))

            # Crear horario por defecto (07:45 con 15 min tolerancia)
            try:
                horario = HorarioFuncionario.objects.create(
                    funcionario=user,
                    hora_entrada=time(7, 45),
                    activo=True
                )
                print("Horario creado: {}".format(horario.hora_entrada))
                created_schedules += 1

            except Exception as e:
                errors.append("Error creando horario para {}: {}".format(user.get_full_name(), e))

            created_users += 1

        except Exception as e:
            errors.append("Error creando usuario {}: {}".format(user_data['full_name'], e))

    return created_users, created_schedules, errors

def main():
    print("IMPORTANDO USUARIOS DESDE EXCEL")
    print("=" * 60)

    # 1. Extraer usuarios del Excel
    users_data = extract_unique_users_from_excel()
    if not users_data:
        return

    # 2. Mostrar preview
    print("\nUsuarios a importar: {}".format(len(users_data)))
    print("Primeros 5:")
    for i, (rut, data) in enumerate(list(users_data.items())[:5]):
        print("{}. {} - {}".format(i+1, data['rut_display'], data['full_name']))
    print("    ...")

    # 3. Confirmar importación
    try:
        confirm = input("\nImportar {} usuarios? (y/N): ".format(len(users_data))).lower().strip()
    except:
        confirm = 'n'

    if confirm not in ['y', 'yes', 's', 'si']:
        print("Importacion cancelada")
        return

    # 4. Crear usuarios
    print("\nCreando usuarios...")
    created_users, created_schedules, errors = create_users_and_schedules(users_data)

    # 5. Resultado
    print("\n" + "=" * 60)
    print("RESULTADO DE IMPORTACION:")
    print("   Usuarios creados: {}".format(created_users))
    print("   Horarios creados: {}".format(created_schedules))
    print("   Errores: {}".format(len(errors)))

    if errors:
        print("\nErrores encontrados:")
        for error in errors[:5]:
            print("   {}".format(error))
        if len(errors) > 5:
            print("   ... y {} mas".format(len(errors) - 5))

    # 6. Verificar resultado final
    total_users = CustomUser.objects.count()
    total_schedules = HorarioFuncionario.objects.count()

    print("\nESTADO FINAL:")
    print("   Total usuarios en BD: {}".format(total_users))
    print("   Total horarios en BD: {}".format(total_schedules))

    if created_users > 0:
        print("\nIMPORTACION EXITOSA")
        print("Ahora puedes:")
        print("   1. Subir el Excel de asistencia")
        print("   2. Ver estadisticas en 'Mi Asistencia'")
        print("   3. Gestionar horarios en 'Gestion de Horarios'")
        print("\nIMPORTANTE: Cambia las contraseñas de los usuarios creados")
    else:
        print("\nNo se crearon usuarios")

if __name__ == '__main__':
    main()
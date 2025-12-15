#!/usr/bin/env python
"""
Script para probar la carga de asistencia directamente sin formulario
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from asistencia.views import CargaRegistrosAsistenciaView
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from users.models import CustomUser
from django.core.files.uploadedfile import SimpleUploadedFile
import io

def test_direct_upload():
    print("🧪 Probando carga directa de asistencia...")
    print("=" * 50)

    # Crear request factory
    factory = RequestFactory()

    # Obtener un usuario admin
    try:
        admin_user = CustomUser.objects.filter(role='ADMIN').first()
        if not admin_user:
            admin_user = CustomUser.objects.filter(role='SECRETARIA').first()
        if not admin_user:
            admin_user = CustomUser.objects.first()

        if not admin_user:
            print("❌ No hay usuarios en la base de datos")
            return

        print(f"✅ Usuario encontrado: {admin_user.get_full_name()} ({admin_user.role})")

    except Exception as e:
        print(f"❌ Error obteniendo usuario: {e}")
        return

    # Simular archivo Excel (crear uno simple)
    try:
        # Crear datos de prueba simples
        test_data = """R.U.T.,Nombre,Horario
17639211-8,MARCO ROSAS VILLARRO,01-11-2025 08:00
17639211-8,MARCO ROSAS VILLARRO,01-11-2025 17:00
"""

        # Crear archivo en memoria
        file_content = test_data.encode('utf-8')
        uploaded_file = SimpleUploadedFile(
            "test.xlsx",
            file_content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        print("✅ Archivo de prueba creado")

    except Exception as e:
        print(f"❌ Error creando archivo de prueba: {e}")
        return

    # Crear request POST
    try:
        request = factory.post(
            '/asistencia/cargar-registros/',
            {
                'archivo_excel': uploaded_file,
                'mes': '11',
                'anio': '2025'
            }
        )
        request.user = admin_user

        print("✅ Request POST creado")

    except Exception as e:
        print(f"❌ Error creando request: {e}")
        return

    # Crear vista y procesar
    try:
        view = CargaRegistrosAsistenciaView()
        view.request = request

        # Simular form_valid
        form_data = {
            'archivo_excel': uploaded_file,
            'mes': '11',
            'anio': '2025'
        }

        from asistencia.forms import CargaRegistrosAsistenciaForm
        form = CargaRegistrosAsistenciaForm(form_data, {'archivo_excel': uploaded_file})

        if form.is_valid():
            print("✅ Formulario válido")
            registros_creados, errores = view.procesar_excel_asistencia(uploaded_file, 11, 2025)
            print(f"📊 Resultado: {registros_creados} registros creados, {len(errores)} errores")

            if errores:
                print("❌ Errores encontrados:")
                for error in errores[:5]:
                    print(f"   {error}")
        else:
            print("❌ Formulario inválido:")
            print(form.errors)

    except Exception as e:
        print(f"❌ Error procesando: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_direct_upload()
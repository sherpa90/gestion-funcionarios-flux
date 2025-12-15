#!/usr/bin/env python
"""
Script para probar el modelo de asistencia y verificar que funciona correctamente
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from asistencia.models import RegistroAsistencia, HorarioFuncionario
from users.models import CustomUser
from datetime import date, time

def test_model():
    print("🧪 Probando modelo de asistencia...")
    print("=" * 50)

    # Buscar un usuario existente
    try:
        user = CustomUser.objects.first()
        if not user:
            print("❌ No hay usuarios en la base de datos")
            return

        print(f"✅ Usuario encontrado: {user.get_full_name()} (RUT: {user.run})")

        # Crear un registro de asistencia de prueba
        try:
            registro = RegistroAsistencia(
                funcionario=user,
                fecha=date.today(),
                hora_entrada_real=time(8, 30)
            )

            # Intentar guardar (esto debería funcionar sin errores)
            registro.save()
            print("✅ Registro de asistencia creado exitosamente")
            print(f"   Estado: {registro.estado}")
            print(f"   Minutos retraso: {registro.minutos_retraso}")

            # Limpiar el registro de prueba
            registro.delete()
            print("✅ Registro de prueba eliminado")

        except Exception as e:
            print(f"❌ Error al crear registro: {e}")
            return

    except Exception as e:
        print(f"❌ Error general: {e}")
        return

    print("\n🎉 Todos los tests pasaron correctamente!")
    print("El modelo de asistencia está funcionando.")

if __name__ == '__main__':
    test_model()
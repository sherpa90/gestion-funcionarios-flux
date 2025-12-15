#!/usr/bin/env python
"""
Script de debug para asistencia - verifica todos los componentes
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
from django.urls import reverse
from django.test import Client
from django.contrib.auth import authenticate, login

def check_database():
    print("🔍 Verificando base de datos...")
    print("-" * 40)

    # Usuarios
    users = CustomUser.objects.all()
    print(f"👥 Usuarios totales: {users.count()}")

    for user in users[:5]:
        print(f"   {user.run} - {user.get_full_name()} ({user.role})")

    # Horarios
    horarios = HorarioFuncionario.objects.all()
    print(f"⏰ Horarios totales: {horarios.count()}")

    for horario in horarios[:3]:
        print(f"   {horario.funcionario.get_full_name()} - {horario.hora_entrada}")

    # Registros
    registros = RegistroAsistencia.objects.all()
    print(f"📋 Registros totales: {registros.count()}")

    return users.count() > 0

def test_model_save():
    print("\n🧪 Probando modelo RegistroAsistencia...")
    print("-" * 40)

    try:
        user = CustomUser.objects.first()
        if not user:
            print("❌ No hay usuarios para probar")
            return False

        print(f"✅ Probando con usuario: {user.get_full_name()}")

        # Crear registro
        registro = RegistroAsistencia(
            funcionario=user,
            fecha=date.today(),
            hora_entrada_real=time(8, 30)
        )

        # Intentar guardar
        registro.save()
        print("✅ Registro guardado exitosamente")
        print(f"   Estado: {registro.estado}")
        print(f"   Retraso: {registro.minutos_retraso} min")

        # Limpiar
        registro.delete()
        print("✅ Registro de prueba eliminado")

        return True

    except Exception as e:
        print(f"❌ Error en modelo: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_view_access():
    print("\n🌐 Probando acceso a vistas...")
    print("-" * 40)

    client = Client()

    # Intentar acceder sin login
    response = client.get('/asistencia/cargar-registros/')
    print(f"❌ Sin login: {response.status_code} (esperado 302)")

    # Intentar login con primer usuario
    user = CustomUser.objects.filter(role__in=['ADMIN', 'SECRETARIA']).first()
    if not user:
        user = CustomUser.objects.first()

    if user:
        print(f"✅ Intentando login con: {user.username}")

        # Login manual
        client.force_login(user)
        response = client.get('/asistencia/cargar-registros/')
        print(f"🔐 Con login: {response.status_code}")

        if response.status_code == 200:
            print("✅ Vista accesible")
            return True
        else:
            print(f"❌ Error accediendo vista: {response.status_code}")
            return False
    else:
        print("❌ No hay usuarios para probar login")
        return False

def main():
    print("🐛 DEBUG COMPLETO - SISTEMA DE ASISTENCIA")
    print("=" * 60)

    # 1. Verificar BD
    has_users = check_database()

    # 2. Probar modelo
    model_works = test_model_save()

    # 3. Probar vistas
    view_works = test_view_access()

    print("\n" + "=" * 60)
    print("📊 RESULTADO FINAL:")
    print(f"   Base de datos: {'✅' if has_users else '❌'}")
    print(f"   Modelo: {'✅' if model_works else '❌'}")
    print(f"   Vistas: {'✅' if view_works else '❌'}")

    if has_users and model_works and view_works:
        print("\n🎉 SISTEMA COMPLETAMENTE FUNCIONAL")
        print("💡 Si hay errores CSRF, recarga la página")
    else:
        print("\n❌ HAY PROBLEMAS TÉCNICOS")
        if not has_users:
            print("   - Crear usuarios en el sistema")
        if not model_works:
            print("   - Ejecutar migraciones: ./run_migrations.sh")
        if not view_works:
            print("   - Verificar permisos de usuario")

if __name__ == '__main__':
    main()
#!/usr/bin/env python
"""
Script maestro para configurar completamente el sistema de asistencia
"""
import os
import sys
import subprocess

def run_command(cmd, description):
    """Ejecuta un comando y muestra el resultado"""
    print("\n" + "="*60)
    print("🚀 {}".format(description))
    print("="*60)

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd='.')

        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print("STDERR:", result.stderr)

        if result.returncode == 0:
            print("✅ {}".format(description))
            return True
        else:
            print("❌ Error en {}".format(description))
            return False

    except Exception as e:
        print("❌ Error ejecutando {}: {}".format(description, e))
        return False

def main():
    print("🎯 CONFIGURACIÓN COMPLETA DEL SISTEMA DE ASISTENCIA")
    print("="*80)

    # 1. Ejecutar migraciones
    if not run_command("./run_migrations.sh", "EJECUTANDO MIGRACIONES"):
        print("❌ Error en migraciones. Abortando.")
        return

    # 2. Importar usuarios
    if not run_command("python3 import_users_excel.py", "IMPORTANDO USUARIOS DESDE EXCEL"):
        print("❌ Error importando usuarios.")
        return

    # 3. Verificar sistema
    if not run_command("python3 debug_asistencia.py", "VERIFICANDO SISTEMA COMPLETO"):
        print("❌ Error en verificación del sistema.")
        return

    print("\n" + "="*80)
    print("🎉 ¡CONFIGURACIÓN COMPLETADA EXITOSAMENTE!")
    print("="*80)
    print("✅ Migraciones ejecutadas")
    print("✅ Usuarios importados")
    print("✅ Sistema verificado")
    print()
    print("🚀 El sistema de asistencia está listo para usar:")
    print("   1. Ve a 'Cargar Registros' y sube el Excel")
    print("   2. Ve a 'Mi Asistencia' para ver estadísticas")
    print("   3. Ve a 'Gestión de Horarios' para ajustar horarios")
    print()
    print("⚠️  RECUERDA:")
    print("   - Cambiar contraseñas de usuarios (actualmente '123456')")
    print("   - Si hay error CSRF, recarga la página")
    print("   - Los usuarios tienen rol 'FUNCIONARIO' por defecto")

if __name__ == '__main__':
    main()
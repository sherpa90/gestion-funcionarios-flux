import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import CustomUser
from asistencia.models import HorarioFuncionario
from datetime import time

def setup_default_horarios():
    """
    Crea horarios de entrada predeterminados para todos los usuarios que no tengan uno.
    Horario predeterminado: 07:45 AM con 5 minutos de tolerancia.
    """
    print("=== Configurando Horarios Predeterminados ===")
    print(f"Total de usuarios: {CustomUser.objects.count()}")
    
    # Obtener usuarios sin horario
    usuarios_sin_horario = []
    for user in CustomUser.objects.all():
        if not HorarioFuncionario.objects.filter(funcionario=user).exists():
            usuarios_sin_horario.append(user)
    
    print(f"Usuarios sin horario: {len(usuarios_sin_horario)}")
    
    # Crear horarios predeterminados
    if usuarios_sin_horario:
        print("\nCreando horarios predeterminados (07:45 AM - 5 min tolerancia)...")
        horarios_creados = 0
        
        for user in usuarios_sin_horario:
            try:
                HorarioFuncionario.objects.create(
                    funcionario=user,
                    hora_entrada=time(7, 45),
                    tolerancia_minutos=5,
                    activo=True
                )
                horarios_creados += 1
                print(f"✅ Horario creado para: {user.get_full_name()}")
            except Exception as e:
                print(f"❌ Error al crear horario para {user.get_full_name()}: {e}")
        
        print(f"\nTotal horarios creados: {horarios_creados}")
    else:
        print("\nTodos los usuarios ya tienen horarios asignados.")
    
    # Verificar total de horarios
    total_horarios = HorarioFuncionario.objects.count()
    print(f"\nTotal de horarios en sistema: {total_horarios}")
    
    # Mostrar estadísticas
    horarios_activos = HorarioFuncionario.objects.filter(activo=True).count()
    print(f"Horarios activos: {horarios_activos}")
    horarios_inactivos = HorarioFuncionario.objects.filter(activo=False).count()
    print(f"Horarios inactivos: {horarios_inactivos}")
    
    # Mostrar horarios creados
    print("\n=== Horarios Creados ===")
    for horario in HorarioFuncionario.objects.all():
        print(f"{horario.funcionario.get_full_name()} - {horario.hora_entrada.strftime('%H:%M')} "
              f"(Tol: {horario.tolerancia_minutos} min) - "
              f"{'Activo' if horario.activo else 'Inactivo'}")

if __name__ == "__main__":
    setup_default_horarios()

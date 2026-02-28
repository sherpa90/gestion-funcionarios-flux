from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from asistencia.models import HorarioFuncionario
from datetime import time

@receiver(post_save, sender=get_user_model())
def create_default_horario(sender, instance, created, **kwargs):
    """Crea un horario por defecto (07:45 AM) cuando se crea un nuevo usuario"""
    if created:
        try:
            HorarioFuncionario.objects.create(
                funcionario=instance,
                hora_entrada=time(7, 45),
                tolerancia_minutos=5,
                activo=True
            )
        except Exception as e:
            print(f"Error al crear horario para {instance.get_full_name()}: {e}")

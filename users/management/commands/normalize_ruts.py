from django.core.management.base import BaseCommand
from users.models import CustomUser
from core.utils import normalize_rut

class Command(BaseCommand):
    help = 'Normaliza todos los RUTs existentes en la base de datos al formato chileno con puntos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar cambios sin aplicarlos',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write('🔍 MODO PRUEBA - No se aplicarán cambios')
        else:
            self.stdout.write('🔄 Normalizando RUTs existentes...')

        self.stdout.write('=' * 60)

        usuarios_actualizados = 0
        usuarios_procesados = 0

        # Mostrar estado inicial
        self.stdout.write('📊 Estado inicial de RUTs:')
        for user in CustomUser.objects.all()[:5]:  # Mostrar primeros 5
            self.stdout.write(f'  {user.run} - {user.get_full_name()}')
        self.stdout.write('')

        # Normalizar todos los RUTs al formato chileno con puntos
        for user in CustomUser.objects.all():
            usuarios_procesados += 1
            rut_original = user.run
            rut_normalizado = normalize_rut(rut_original)

            if rut_original != rut_normalizado:
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f'🔄 Se normalizaría: {user.get_full_name()}: {rut_original} → {rut_normalizado}'
                        )
                    )
                else:
                    user.run = rut_normalizado
                    user.save(update_fields=['run'])
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ {user.get_full_name()}: {rut_original} → {rut_normalizado}'
                        )
                    )
                usuarios_actualizados += 1

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'🎯 Simulación completada: {usuarios_actualizados} usuarios necesitan normalización'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'🎉 Normalización completada: {usuarios_actualizados} de {usuarios_procesados} usuarios actualizados'
                )
            )
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
import os


class Command(BaseCommand):
    help = "Asegura que la app de Google OAuth exista en la base de datos"

    def handle(self, *args, **options):
        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        secret = os.environ.get('GOOGLE_CLIENT_SECRET')

        if not client_id or not secret:
            self.stdout.write(self.style.WARNING("GOOGLE_CLIENT_ID o GOOGLE_CLIENT_SECRET no estan configurados."))
            return

        site = Site.objects.get_current()

        app, created = SocialApp.objects.get_or_create(
            provider='google',
            defaults={
                'name': 'Google',
                'client_id': client_id,
                'secret': secret,
            }
        )

        if not created:
            app.client_id = client_id
            app.secret = secret
            app.save()

        if site not in app.sites.all():
            app.sites.add(site)

        self.stdout.write(self.style.SUCCESS(f"SocialApp Google lista para dominio: {site.domain}"))

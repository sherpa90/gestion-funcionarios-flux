# Generated manually for jornada field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('permisos', '0005_solicitudpermiso_cancelled_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitudpermiso',
            name='jornada',
            field=models.CharField(choices=[('AM', 'Mañana'), ('PM', 'Tarde'), ('FD', 'Día Completo')], default='FD', help_text='Jornada del permiso (solo aplica para medio día)', max_length=2),
        ),
    ]
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('licencias', '0003_licenciamedica_archivo'),
    ]

    operations = [
        migrations.AddField(
            model_name='licenciamedica',
            name='tipo',
            field=models.CharField(choices=[('LICENCIA', 'Licencia Médica'), ('PERMISO', 'Permiso sin Goce de Remuneraciones')], default='LICENCIA', max_length=20),
        ),
    ]

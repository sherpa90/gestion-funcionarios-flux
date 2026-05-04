from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('admin_dashboard', '0002_efemeride'),
    ]

    operations = [
        migrations.AddField(
            model_name='efemeride',
            name='fecha_hasta',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha Hasta'),
        ),
    ]

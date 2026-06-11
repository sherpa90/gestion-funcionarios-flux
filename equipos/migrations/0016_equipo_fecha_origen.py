# Generated manually for fecha_origen field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('equipos', '0006_alter_equipo_numero_inventario_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='equipo',
            name='fecha_origen',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha de Origen'),
        ),
    ]

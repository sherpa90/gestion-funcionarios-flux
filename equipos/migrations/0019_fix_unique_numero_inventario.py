# Generated manually to fix unique constraint on numero_inventario/numero_serie
from django.conf import settings
from django.db import migrations, models


def normalize_equipo_codes(apps, schema_editor):
    Equipo = apps.get_model('equipos', 'Equipo')
    Equipo.objects.filter(numero_inventario='').update(numero_inventario=None)
    Equipo.objects.filter(numero_serie='').update(numero_serie=None)


class Migration(migrations.Migration):

    dependencies = [
        ('equipos', '0018_prestamoequipo_es_prestamo_diario_and_more'),
    ]

    operations = [
        migrations.RunPython(
            code=normalize_equipo_codes,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='equipo',
            name='numero_inventario',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True, verbose_name='Número de Inventario'),
        ),
        migrations.AlterField(
            model_name='equipo',
            name='numero_serie',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True, verbose_name='Número de Serie'),
        ),
    ]

    # Avoid Django wrapping this migration in a single transaction,
    # which can trigger PostgreSQL "pending trigger events" on ALTER TABLE.
    atomic = False

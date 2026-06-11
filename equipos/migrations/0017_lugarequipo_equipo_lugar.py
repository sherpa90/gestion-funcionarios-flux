# Generated manually for lugar_equipo model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('equipos', '0016_equipo_fecha_origen'),
    ]

    operations = [
        migrations.CreateModel(
            name='LugarEquipo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True, verbose_name='Nombre del Lugar')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('activo', models.BooleanField(default=True, verbose_name='Activo')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('creado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lugares_equipos_creados', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Lugar de Equipo',
                'verbose_name_plural': 'Lugares de Equipos',
                'ordering': ['nombre'],
            },
        ),
        migrations.AddField(
            model_name='equipo',
            name='lugar',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='equipos', to='equipos.lugarequipo', verbose_name='Lugar'),
        ),
    ]

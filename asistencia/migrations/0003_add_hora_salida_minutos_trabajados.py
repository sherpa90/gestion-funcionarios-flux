# Generated manually for adding hora_salida_real and minutos_trabajados fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('asistencia', '0002_remove_registroasistencia_unique_funcionario_fecha_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='registroasistencia',
            name='hora_salida_real',
            field=models.TimeField(blank=True, help_text='Hora de salida registrada por el reloj control', null=True),
        ),
        migrations.AddField(
            model_name='registroasistencia',
            name='minutos_trabajados',
            field=models.IntegerField(blank=True, default=0, help_text='Minutos trabajados calculados'),
        ),
    ]

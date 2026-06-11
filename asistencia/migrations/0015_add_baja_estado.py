# Generated manually for baja status

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('asistencia', '0014_alter_diahorario_unique_together_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registroasistencia',
            name='estado',
            field=models.CharField(choices=[('PUNTUAL', 'Puntual'), ('RETRASO', 'Retraso'), ('AUSENTE', 'Ausente'), ('JUSTIFICADO', 'Justificado'), ('SIN_MARCACION_ENTRADA', 'Sin Marcación de Entrada'), ('MEDIO_DIA', 'Medio Día Administrativo'), ('DIA_ADMINISTRATIVO', 'Día Administrativo'), ('LICENCIA_MEDICA', 'Licencia Médica'), ('BAJA', 'Baja'), ('DIA_FESTIVO', 'Día Festivo'), ('SIN_HORARIO', 'Sin Horario Asignado'), ('SIN_DATA', 'Sin Datos')], default='AUSENTE', max_length=25),
        ),
    ]

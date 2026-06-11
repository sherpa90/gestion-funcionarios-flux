# Generated manually for baja/alta functionality

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_alter_customuser_funcion'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='is_on_leave',
            field=models.BooleanField(default=False, help_text='Si está marcado, el funcionario está de baja'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='baja_date',
            field=models.DateField(blank=True, help_text='Fecha de inicio de la baja', null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='alta_date',
            field=models.DateField(blank=True, help_text='Fecha de alta/reingreso', null=True),
        ),
    ]

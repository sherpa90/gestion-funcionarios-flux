from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('asistencia', '0017_horarioexcepcional_es_para_serenos'),
    ]

    operations = [
        migrations.AlterField(
            model_name='horarioexcepcional',
            name='es_para_serenos',
            field=models.CharField(
                choices=[
                    ('TODOS', 'Todos los funcionarios'),
                    ('FUNCIONARIOS', 'Solo funcionarios (no serenos)'),
                    ('SERENOS', 'Solo serenos'),
                ],
                default='TODOS',
                help_text="Grupo de funcionarios al que aplica este horario excepcional",
                max_length=20
            ),
        ),
        migrations.RenameField(
            model_name='horarioexcepcional',
            old_name='es_para_serenos',
            new_name='aplica_a',
        ),
    ]

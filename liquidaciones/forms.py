from django import forms
from django.core.validators import FileExtensionValidator

class CargaLiquidacionesForm(forms.Form):
    archivo = forms.FileField(
        label='Archivo PDF (Liquidaciones)',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text='Sube un único archivo PDF que contenga todas las liquidaciones.'
    )
    mes = forms.ChoiceField(
        choices=[
            (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
            (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
            (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
        ],
        label='Mes'
    )
    anio = forms.IntegerField(
        label='Año',
        min_value=2020,
        max_value=2030
    )

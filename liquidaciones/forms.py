from django import forms
from django.core.validators import FileExtensionValidator

class CargaLiquidacionesForm(forms.Form):
    archivo = forms.FileField(
        label='Archivo PDF (Liquidaciones)',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text='Sube un único archivo PDF que contenga todas las liquidaciones.',
        widget=forms.FileInput(attrs={
            "class": "block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100",
            "accept": ".pdf"
        })
    )
    mes = forms.ChoiceField(
        choices=[
            (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
            (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
            (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
        ],
        label='Mes',
        widget=forms.Select(attrs={
            "class": "mt-1 block w-full h-11 px-4 py-2 border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500 bg-white"
        })
    )
    anio = forms.IntegerField(
        label='Año',
        min_value=2020,
        max_value=2030,
        widget=forms.NumberInput(attrs={
            "class": "mt-1 block w-full h-11 px-4 py-2 border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500 bg-white"
        })
    )

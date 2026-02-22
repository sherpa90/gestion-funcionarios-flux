from django import forms
from .models import LicenciaMedica
from users.models import CustomUser

class LicenciaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar el queryset para mostrar RUN y nombre de todos los usuarios
        self.fields['usuario'].queryset = CustomUser.objects.all().order_by('last_name', 'first_name')
        self.fields['usuario'].label_from_instance = lambda obj: f"{obj.run} - {obj.get_full_name()}"
    
    usuario = forms.ModelChoiceField(
        queryset=CustomUser.objects.all().order_by('last_name', 'first_name'),
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-5 py-4 bg-gray-50 border-none rounded-2xl text-sm font-black text-gray-700 focus:ring-2 focus:ring-blue-100 transition-all uppercase tracking-widest'
        }),
        help_text="Solo para Secretaria: selecciona el usuario al que pertenece la licencia"
    )
    
    class Meta:
        model = LicenciaMedica
        fields = ['usuario', 'fecha_inicio', 'dias', 'archivo']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'w-full px-5 py-4 bg-gray-50 border-none rounded-2xl text-sm font-black text-gray-700 focus:ring-2 focus:ring-blue-100 transition-all uppercase tracking-widest'
            }),
            'dias': forms.NumberInput(attrs={
                'class': 'w-full px-5 py-4 bg-gray-50 border-none rounded-2xl text-sm font-black text-gray-700 focus:ring-2 focus:ring-blue-100 transition-all uppercase tracking-widest'
            }),
            'archivo': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'licencia-file-input',
                'onchange': 'handleFileSelect(this)'
            })
        }

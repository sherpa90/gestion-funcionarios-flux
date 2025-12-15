from django import forms
from .models import LicenciaMedica
from users.models import CustomUser

class LicenciaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar el queryset para mostrar RUN y nombre
        self.fields['usuario'].queryset = CustomUser.objects.filter(role='FUNCIONARIO').order_by('last_name', 'first_name')
        self.fields['usuario'].label_from_instance = lambda obj: f"{obj.run} - {obj.get_full_name()}"
    
    usuario = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role='FUNCIONARIO').order_by('last_name', 'first_name'),
        required=False,
        widget=forms.Select(attrs={'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
        help_text="Solo para Secretaria: selecciona el usuario al que pertenece la licencia"
    )
    
    class Meta:
        model = LicenciaMedica
        fields = ['usuario', 'fecha_inicio', 'dias']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'dias': forms.NumberInput(attrs={'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
        }

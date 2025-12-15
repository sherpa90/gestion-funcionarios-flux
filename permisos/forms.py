from django import forms
from .models import SolicitudPermiso
from core.services import BusinessDayCalculator
from users.models import CustomUser

class SolicitudForm(forms.ModelForm):
    jornada = forms.ChoiceField(
        choices=[('AM', 'Mañana (AM)'), ('PM', 'Tarde (PM)')],
        widget=forms.RadioSelect(attrs={'class': 'jornada-radio'}),
        required=False,
        label='Jornada (medio día)'
    )

    class Meta:
        model = SolicitudPermiso
        fields = ['fecha_inicio', 'dias_solicitados', 'jornada', 'observacion', 'archivo_justificacion']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'dias_solicitados': forms.Select(attrs={'id': 'id_dias_solicitados'}),
            'observacion': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Motivo o justificación de tu solicitud (opcional)'}),
            'archivo_justificacion': forms.FileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}),
        }
        labels = {
            'fecha_inicio': 'Fecha de Inicio',
            'dias_solicitados': 'Días Solicitados',
            'observacion': 'Observación',
            'archivo_justificacion': 'Documento de Respaldo',
        }
        help_texts = {
            'archivo_justificacion': 'Opcional: Sube un documento PDF o imagen (JPG/PNG) para justificar tu solicitud',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # La jornada se controla con JavaScript en el template
        # No ocultamos el campo aquí, lo manejamos con CSS/JS

    def clean_archivo_justificacion(self):
        archivo = self.cleaned_data.get('archivo_justificacion')
        if archivo:
            # Validar tamaño (máximo 5MB)
            if archivo.size > 5 * 1024 * 1024:
                raise forms.ValidationError("El archivo no debe superar los 5MB")
            
            # Validar extensión
            ext = archivo.name.split('.')[-1].lower()
            if ext not in ['pdf', 'jpg', 'jpeg', 'png']:
                raise forms.ValidationError("Solo se permiten archivos PDF, JPG o PNG")
        
        return archivo

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        dias = cleaned_data.get('dias_solicitados')
        jornada = cleaned_data.get('jornada')

        if fecha_inicio and dias:
            if not BusinessDayCalculator.is_business_day(fecha_inicio):
                raise forms.ValidationError("La fecha de inicio debe ser un día hábil.")

        # Validar jornada solo si es medio día
        if dias and dias % 1 == 0.5:  # Si termina en .5
            if not jornada:
                raise forms.ValidationError("Debes seleccionar la jornada (mañana o tarde) para permisos de medio día.")
            if jornada not in ['AM', 'PM']:
                raise forms.ValidationError("La jornada debe ser AM o PM para permisos de medio día.")

        return cleaned_data

class SolicitudBypassForm(forms.ModelForm):
    """Formulario para que Secretaria ingrese permisos a nombre de otros usuarios"""
    jornada = forms.ChoiceField(
        choices=[('AM', 'Mañana (AM)'), ('PM', 'Tarde (PM)')],
        widget=forms.RadioSelect(attrs={'class': 'jornada-radio'}),
        required=False,
        label='Jornada (medio día)'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar el queryset para mostrar RUN y nombre
        self.fields['usuario'].queryset = CustomUser.objects.filter(role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA']).order_by('last_name', 'first_name')
        self.fields['usuario'].label_from_instance = lambda obj: f"{obj.run} - {obj.get_full_name()}"

        # La jornada se controla con JavaScript en el template
        # No ocultamos el campo aquí, lo manejamos con CSS/JS

    usuario = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA']).order_by('last_name', 'first_name'),
        widget=forms.Select(attrs={'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
        label="Usuario"
    )

    class Meta:
        model = SolicitudPermiso
        fields = ['usuario', 'fecha_inicio', 'dias_solicitados', 'jornada', 'observacion']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'dias_solicitados': forms.Select(attrs={'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm', 'id': 'id_dias_solicitados'}),
            'observacion': forms.Textarea(attrs={'rows': 3, 'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm', 'placeholder': 'Motivo o comentarios (opcional)'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        dias = cleaned_data.get('dias_solicitados')
        jornada = cleaned_data.get('jornada')

        if fecha_inicio and dias:
            if not BusinessDayCalculator.is_business_day(fecha_inicio):
                raise forms.ValidationError("La fecha de inicio debe ser un día hábil.")

        # Validar jornada solo si es medio día
        if dias and dias % 1 == 0.5:  # Si termina en .5
            if not jornada:
                raise forms.ValidationError("Debes seleccionar la jornada (mañana o tarde) para permisos de medio día.")
            if jornada not in ['AM', 'PM']:
                raise forms.ValidationError("La jornada debe ser AM o PM para permisos de medio día.")

        return cleaned_data

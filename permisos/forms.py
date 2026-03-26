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
            'fecha_inicio': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-5 py-4 bg-gray-50 border-none rounded-2xl text-sm font-black text-gray-700 focus:ring-2 focus:ring-blue-100 transition-all uppercase tracking-widest'
            }),
            'dias_solicitados': forms.Select(attrs={
                'id': 'id_dias_solicitados',
                'class': 'w-full px-5 py-4 bg-gray-50 border-none rounded-2xl text-sm font-black text-gray-700 focus:ring-2 focus:ring-blue-100 transition-all uppercase tracking-widest'
            }),
            'observacion': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': '¿POR QUÉ NECESITAS ESTOS DÍAS? (OPCIONAL)',
                'class': 'w-full px-5 py-4 bg-gray-50 border-none rounded-2xl text-sm font-black text-gray-700 focus:ring-2 focus:ring-blue-100 transition-all uppercase tracking-widest resize-none'
            }),
            'archivo_justificacion': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'justificacion-file-input',
                'onchange': 'handleFileSelect(this)',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
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
        self.user = kwargs.pop('user', None)
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
            # Priorizar self.user (pasado desde la vista) o self.instance.usuario
            user = getattr(self, 'user', None) or getattr(self.instance, 'usuario', None)
            if not BusinessDayCalculator.is_business_day(fecha_inicio, user=user):
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
        self.fields['usuario'].queryset = CustomUser.objects.filter(role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA']).order_by('first_name', 'last_name')
        self.fields['usuario'].label_from_instance = lambda obj: f"{obj.get_full_name()} - {obj.run}"

        # La jornada se controla con JavaScript en el template
        # No ocultamos el campo aquí, lo manejamos con CSS/JS

    usuario = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA']).order_by('first_name', 'last_name'),
        widget=forms.Select(attrs={
            'class': 'w-full px-5 py-4 bg-gray-50 border-none rounded-2xl text-sm font-black text-gray-700 focus:ring-2 focus:ring-blue-100 transition-all uppercase tracking-widest'
        }),
        label="Usuario"
    )

    class Meta:
        model = SolicitudPermiso
        fields = ['usuario', 'fecha_inicio', 'dias_solicitados', 'jornada', 'observacion']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'w-full px-5 py-4 bg-gray-50 border-none rounded-2xl text-sm font-black text-gray-700 focus:ring-2 focus:ring-blue-100 transition-all uppercase tracking-widest'
            }),
            'dias_solicitados': forms.Select(attrs={
                'class': 'w-full px-5 py-4 bg-gray-50 border-none rounded-2xl text-sm font-black text-gray-700 focus:ring-2 focus:ring-blue-100 transition-all uppercase tracking-widest', 
                'id': 'id_dias_solicitados'
            }),
            'observacion': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'w-full px-5 py-4 bg-gray-50 border-none rounded-2xl text-sm font-black text-gray-700 focus:ring-2 focus:ring-blue-100 transition-all uppercase tracking-widest resize-none', 
                'placeholder': 'MOTIVO O COMENTARIOS (OPCIONAL)'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        dias = cleaned_data.get('dias_solicitados')
        jornada = cleaned_data.get('jornada')

        usuario = cleaned_data.get('usuario')
        if fecha_inicio and dias:
            if not BusinessDayCalculator.is_business_day(fecha_inicio, user=usuario):
                raise forms.ValidationError("La fecha de inicio debe ser un día hábil.")

        # Validar jornada solo si es medio día
        if dias and dias % 1 == 0.5:  # Si termina en .5
            if not jornada:
                raise forms.ValidationError("Debes seleccionar la jornada (mañana o tarde) para permisos de medio día.")
            if jornada not in ['AM', 'PM']:
                raise forms.ValidationError("La jornada debe ser AM o PM para permisos de medio día.")

        return cleaned_data

class SolicitudAdminForm(SolicitudForm):
    """Formulario para edición administrativa - incluye el campo de estado"""
    class Meta(SolicitudForm.Meta):
        fields = SolicitudForm.Meta.fields + ['estado']
        widgets = SolicitudForm.Meta.widgets.copy()
        widgets.update({
            'estado': forms.Select(attrs={
                'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500'
            })
        })

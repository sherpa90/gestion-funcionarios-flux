from django import forms
from .models import SolicitudPermiso
from core.services import BusinessDayCalculator
from users.models import CustomUser
from datetime import date as _date

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
                'min': _date.today().isoformat(),
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
            from core.validators import validate_file_upload
            validate_file_upload(archivo)
        return archivo

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        dias = cleaned_data.get('dias_solicitados')
        jornada = cleaned_data.get('jornada')

        user = getattr(self, 'user', None)
        if user and user.dias_disponibles <= 0:
            raise forms.ValidationError(
                "No puedes solicitar días administrativos. Ya has alcanzado el límite de 6.0 días."
            )

        if fecha_inicio:
            if fecha_inicio < _date.today():
                raise forms.ValidationError(
                    "No puedes solicitar un día administrativo en una fecha pasada. "
                    "La fecha de inicio debe ser hoy o posterior."
                )

            if dias:
                if not BusinessDayCalculator.is_business_day(fecha_inicio, user=user):
                    raise forms.ValidationError("La fecha de inicio debe ser un día hábil.")

        if dias and dias % 1 == 0.5:
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
        self.fields['usuario'].queryset = CustomUser.objects.filter(role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA', 'ADMIN']).order_by('first_name', 'last_name')
        self.fields['usuario'].label_from_instance = lambda obj: f"{obj.get_full_name()} - {obj.run}"

        # La jornada se controla con JavaScript en el template
        # No ocultamos el campo aquí, lo manejamos con CSS/JS

    usuario = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA', 'ADMIN']).order_by('first_name', 'last_name'),
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
                'min': f"{_date.today().year}-01-01",
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

        if fecha_inicio:
            # Para ingreso directo, se permiten fechas pasadas solo si son del año actual
            hoy = _date.today()
            if fecha_inicio < hoy and fecha_inicio.year != hoy.year:
                raise forms.ValidationError(
                    "No puedes ingresar un día administrativo de años anteriores. "
                    "Las fechas pasadas deben corresponder al año en curso."
                )

            if dias:
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
    usuario = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA', 'ADMIN']).order_by('first_name', 'last_name'),
        widget=forms.Select(attrs={
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500'
        }),
        label="Usuario"
    )
    
    class Meta(SolicitudForm.Meta):
        fields = ['usuario', 'fecha_inicio', 'dias_solicitados', 'jornada', 'observacion', 'estado']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={
                'type': 'date',
                'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500'
            }),
            'dias_solicitados': forms.Select(attrs={
                'id': 'id_dias_solicitados',
                'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500',
            }),
            'observacion': forms.Textarea(attrs={
                'rows': 3,
                'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500'
            }),
            'estado': forms.Select(attrs={
                'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500'
            })
        }
    
    def clean(self):
        # Permitir fechas pasadas en edición administrativa
        cleaned_data = super(SolicitudForm, self).clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        dias = cleaned_data.get('dias_solicitados')
        jornada = cleaned_data.get('jornada')
        usuario = cleaned_data.get('usuario')

        if fecha_inicio and dias:
            user = usuario or getattr(self, 'instance', None) and getattr(self.instance, 'usuario', None)
            if not BusinessDayCalculator.is_business_day(fecha_inicio, user=user):
                raise forms.ValidationError("La fecha de inicio debe ser un día hábil.")

        if dias and dias % 1 == 0.5:
            if not jornada:
                raise forms.ValidationError("Debes seleccionar la jornada (mañana o tarde) para permisos de medio día.")
            if jornada not in ['AM', 'PM']:
                raise forms.ValidationError("La jornada debe ser AM o PM para permisos de medio día.")

        return cleaned_data

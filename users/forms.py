from django import forms
from django.core.exceptions import ValidationError
from .models import CustomUser


class UserCreateForm(forms.ModelForm):
    """Formulario para crear nuevos usuarios"""
    run = forms.CharField(
        help_text="RUN con formato chileno (ej: 12.345.678-K)"
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        help_text="Contraseña temporal que se generará"
    )
    
    class Meta:
        model = CustomUser
        fields = ['run', 'email', 'first_name', 'last_name', 'role', 'tipo_funcionario']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        widgets = {
            'run': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'email': forms.EmailInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'first_name': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'last_name': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'role': forms.Select(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'tipo_funcionario': forms.Select(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
        }
        for field_name, widget in widgets.items():
            self.fields[field_name].widget.attrs.update({'class': widget.attrs.get('class', '')})
    
    def clean_run(self):
        run = self.cleaned_data.get('run')
        if run:
            # Validar formato de RUT chileno
            run = run.upper().replace('.', '').replace('-', '')
            if not self._validate_rut(run):
                raise ValidationError('El RUN no es válido')
        return run
    
    def _validate_rut(self, rut):
        """Valida un RUT chileno"""
        if len(rut) < 2:
            return False
        body = rut[:-1]
        check = rut[-1]
        
        if not body.isdigit():
            return False
        
        sum_ = 0
        multiplier = 2
        for digit in reversed(body):
            sum_ += int(digit) * multiplier
            multiplier = multiplier + 1 if multiplier < 7 else 2
        
        remainder = sum_ % 11
        check_digit = 11 - remainder if remainder > 0 else 0
        
        if check_digit == 10:
            expected_check = 'K'
        else:
            expected_check = str(check_digit)
        
        return check == expected_check
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Validar que el correo sea del dominio correcto
            if not email.endswith('@losalercespuertomontt.cl'):
                raise ValidationError('El correo debe ser del dominio @losalercespuertomontt.cl')
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        # Generar contraseña temporal
        password = self.cleaned_data.get('password', None)
        if password:
            user.set_password(password)
        else:
            import random
            import string
            temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            user.set_password(temp_password)
        
        if commit:
            user.save()
        # Guardar la contraseña generada para mostrarla
        user.generated_password = password if password else temp_password
        return user


class UserEditForm(forms.ModelForm):
    """Formulario para editar usuarios - permite editar RUT para ADMIN y SECRETARIA"""
    
    class Meta:
        model = CustomUser
        fields = ['run', 'email', 'first_name', 'last_name', 'role', 'tipo_funcionario', 'dias_disponibles']
    
    def __init__(self, *args, **kwargs):
        # Extract editing user to check permissions
        editing_user = kwargs.pop('editing_user', None)
        super().__init__(*args, **kwargs)
        
        # Set widgets
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'first_name': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'last_name': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'role': forms.Select(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'tipo_funcionario': forms.Select(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'dias_disponibles': forms.NumberInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm', 'step': '0.5', 'min': '0', 'max': '6'}),
        }
        
        for field_name, widget in widgets.items():
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({'class': widget.attrs.get('class', '')})
        
        # Set initial value for run field
        if self.instance and self.instance.pk:
            self.fields['run'].initial = self.instance.run
        
        # Allow ADMIN and SECRETARIA to edit RUT
        if editing_user and editing_user.role in ['ADMIN', 'SECRETARIA']:
            self.fields['run'].required = False
            self.fields['run'].widget = forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'
            })
            self.fields['run'].help_text = "RUN con formato chileno (ej: 12.345.678-K)"
        else:
            self.fields['run'].required = False
            self.fields['run'].widget = forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm bg-gray-100',
                'readonly': True
            })
            self.fields['run'].help_text = "El RUN no puede ser modificado (formato chileno: 12.345.678-K)"
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Validar que el correo sea del dominio correcto
            if not email.endswith('@losalercespuertomontt.cl'):
                raise ValidationError('El correo debe ser del dominio @losalercespuertomontt.cl')
        return email


class BulkUserImportForm(forms.Form):
    """Formulario para importación masiva de usuarios desde Excel"""
    excel_file = forms.FileField(
        label='Archivo Excel',
        help_text='Sube un archivo Excel (.xlsx) con los datos de usuarios',
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
            'accept': '.xlsx,.xls'
        })
    )
    
    def clean_excel_file(self):
        file = self.cleaned_data.get('excel_file')
        if file:
            # Validar extensión
            if not file.name.endswith(('.xlsx', '.xls')):
                raise ValidationError('El archivo debe ser un Excel (.xlsx o .xls)')
            # Validar tamaño (max 5MB)
            if file.size > 5 * 1024 * 1024:
                raise ValidationError('El archivo no debe superar los 5MB')
        return file

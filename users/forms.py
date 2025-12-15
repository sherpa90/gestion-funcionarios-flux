from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import CustomUser
import random
import string

class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm',
            'placeholder': 'Dejar vacío para generar automáticamente'
        }),
        help_text='Dejar vacío para generar una contraseña segura automáticamente'
    )
    
    class Meta:
        model = CustomUser
        fields = ['run', 'email', 'first_name', 'last_name', 'password', 'role', 'tipo_funcionario', 'dias_disponibles']
        widgets = {
            'run': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm', 'placeholder': '12345678-K'}),
            'email': forms.EmailInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm', 'placeholder': 'usuario@losalercespuertomontt.cl'}),
            'first_name': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'last_name': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'role': forms.Select(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'tipo_funcionario': forms.Select(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'dias_disponibles': forms.NumberInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm', 'step': '0.5', 'min': '0', 'max': '6'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Establecer valor por defecto de 6 días
        if not self.instance.pk:  # Solo para nuevos usuarios
            self.fields['dias_disponibles'].initial = 6

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Validar que el correo sea del dominio correcto
            if not email.endswith('@losalercespuertomontt.cl'):
                raise ValidationError('El correo debe ser del dominio @losalercespuertomontt.cl')
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        # Validar longitud mínima si se proporciona  
        if password and len(password) < 6:
            raise ValidationError('La contraseña debe tener al menos 6 caracteres')
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        # Usar contraseña proporcionada o generar una aleatoria
        password = self.cleaned_data.get('password')
        if not password:
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        user.set_password(password)
        user.username = user.run  # USERNAME_FIELD es run, pero también necesitamos username
        if commit:
            user.save()
        # Guardar la contraseña generada para mostrarla
        user.generated_password = password
        return user

class UserEditForm(forms.ModelForm):
    run = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm bg-gray-100',
            'readonly': True
        }),
        help_text="El RUN no puede ser modificado (formato chileno: 12.345.678-K)"
    )

    class Meta:
        model = CustomUser
        fields = ['run', 'email', 'first_name', 'last_name', 'role', 'tipo_funcionario', 'dias_disponibles']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial value for run field
        if self.instance and self.instance.pk:
            self.fields['run'].initial = self.instance.run
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'first_name': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'last_name': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'role': forms.Select(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'tipo_funcionario': forms.Select(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm'}),
            'dias_disponibles': forms.NumberInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary sm:text-sm', 'step': '0.5', 'min': '0', 'max': '6'}),
        }

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
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, GrupoCorreo


class CustomUserCreationForm(UserCreationForm):
    """
    Formulario para crear usuarios con validación de RUT.
    """
    class Meta:
        model = CustomUser
        fields = ('email', 'run', 'first_name', 'last_name', 'role', 'tipo_funcionario')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer password opcional para admins que crean usuarios
        self.fields['password1'].required = False
        self.fields['password2'].required = False

    def clean_password2(self):
        # Permitir creación sin contraseña
        return self.cleaned_data.get('password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        # Si no hay contraseña, generar una temporal
        if not self.cleaned_data.get('password1'):
            import secrets
            temp_password = secrets.token_urlsafe(8)
            user.set_password(temp_password)
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """
    Formulario para modificar usuarios.
    """
    class Meta:
        model = CustomUser
        fields = ('email', 'run', 'first_name', 'last_name', 'role', 
                  'tipo_funcionario', 'dias_disponibles', 'is_active', 
                  'is_staff', 'groups', 'user_permissions')


class PasswordChangeForm(UserChangeForm):
    """
    Formulario para cambiar contraseña desde el admin.
    """
    class Meta:
        model = CustomUser
        fields = ('password',)

    def clean_password(self):
        # No hacer nada especial con la contraseña
        return self.cleaned_data['password']


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """
    Admin personalizado para CustomUser.
    Permite a administradores crear y cambiar contraseñas de usuarios.
    """
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    change_password_form = PasswordChangeForm
    
    list_display = ('email', 'run', 'first_name', 'last_name', 'telefono', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff', 'tipo_funcionario')
    search_fields = ('email', 'run', 'first_name', 'last_name', 'telefono')
    ordering = ('last_name', 'first_name')
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('email', 'run', 'first_name', 'last_name', 'telefono')
        }),
        ('Rol y Permisos', {
            'fields': ('role', 'tipo_funcionario', 'dias_disponibles', 
                      'is_active', 'is_staff', 'is_superuser',
                      'groups', 'user_permissions')
        }),
        ('Contraseña', {
            'fields': ('password',),
            'classes': ('collapse',),
        }),
        ('Fechas Importantes', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    add_fieldsets = (
        ('Crear Nuevo Usuario', {
            'classes': ('wide',),
            'fields': ('email', 'run', 'first_name', 'last_name', 'telefono',
                      'role', 'tipo_funcionario', 'dias_disponibles')
        }),
    )
    
    filter_horizontal = ('groups', 'user_permissions',)
    
    def get_form(self, request, obj=None, **kwargs):
        """
        Ocultar campos de permisos a usuarios no superusers.
        """
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            if 'user_permissions' in form.base_fields:
                form.base_fields['user_permissions'].queryset = form.base_fields['user_permissions'].queryset.none()
            if 'is_superuser' in form.base_fields:
                form.base_fields['is_superuser'].disabled = True
        return form
    
    def has_change_permission(self, request, obj=None):
        """
        Permitir que ADMIN y SECRETARIA puedan editar usuarios.
        """
        if obj is None:
            return True
        if request.user.role in ['ADMIN', 'SECRETARIA']:
            return True
        return False
    
    def has_add_permission(self, request):
        """
        Permitir que ADMIN y SECRETARIA puedan agregar usuarios.
        """
        if request.user.role in ['ADMIN', 'SECRETARIA']:
            return True
        return False
    
    def has_delete_permission(self, request, obj=None):
        """
        Permitir que solo ADMIN pueda eliminar usuarios.
        """
        if request.user.role == 'ADMIN':
            return True
        return False
    
    def get_readonly_fields(self, request, obj=None):
        """
        Hacer readonly ciertos campos según el rol del admin.
        """
        readonly = list(super().get_readonly_fields(request, obj))
        
        # SECRETARIA no puede cambiar is_staff ni is_superuser
        if request.user.role == 'SECRETARIA':
            readonly.extend(['is_staff', 'is_superuser'])
        
        return readonly
    
    def get_urls(self):
        urls = super().get_urls()
        return urls


@admin.register(GrupoCorreo)
class GrupoCorreoAdmin(admin.ModelAdmin):
    """Admin para grupos de correo"""
    list_display = ('nombre', 'correo', 'cantidad_miembros', 'creado_por', 'activo', 'fecha_creacion')
    list_filter = ('activo', 'fecha_creacion')
    search_fields = ('nombre', 'correo', 'descripcion')
    ordering = ('nombre',)
    filter_horizontal = ('miembros',)
    date_hierarchy = 'fecha_creacion'
    
    fieldsets = (
        ('Información del Grupo', {
            'fields': ('nombre', 'correo', 'descripcion', 'activo')
        }),
        ('Miembros', {
            'fields': ('miembros',)
        }),
        ('Metadatos', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    
    def has_add_permission(self, request):
        if request.user.role in ['ADMIN', 'SECRETARIA']:
            return True
        return False
    
    def has_change_permission(self, request, obj=None):
        if request.user.role in ['ADMIN', 'SECRETARIA']:
            return True
        return False
    
    def has_delete_permission(self, request, obj=None):
        if request.user.role == 'ADMIN':
            return True
        return False
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)

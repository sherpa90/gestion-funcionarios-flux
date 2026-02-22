from django.contrib import admin
from .models import Equipo, PrestamoEquipo


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = [
        'numero_inventario',
        'marca',
        'modelo',
        'tipo',
        'estado',
        'fecha_creacion'
    ]
    list_filter = ['tipo', 'estado', 'marca']
    search_fields = [
        'numero_inventario',
        'numero_serie',
        'marca',
        'modelo'
    ]
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    ordering = ['-fecha_creacion']


@admin.register(PrestamoEquipo)
class PrestamoEquipoAdmin(admin.ModelAdmin):
    list_display = [
        'equipo',
        'funcionario',
        'fecha_asignacion',
        'fecha_devolucion',
        'activo'
    ]
    list_filter = ['activo', 'fecha_asignacion']
    search_fields = [
        'equipo__numero_inventario',
        'funcionario__first_name',
        'funcionario__last_name',
        'funcionario__run'
    ]
    readonly_fields = ['fecha_asignacion']
    ordering = ['-fecha_asignacion']

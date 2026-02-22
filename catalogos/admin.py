from django.contrib import admin
from .models import (
    RolUsuario,
    TipoFuncionario,
    EstadoRegistroAsistencia,
    EstadoSolicitudPermiso,
    TipoEquipo,
    EstadoEquipo,
    PeriodoLiquidacion,
    JornadaLaboral,
    TipoDia,
)


@admin.register(RolUsuario)
class RolUsuarioAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'nivel_acceso', 'activo', 'orden']
    list_filter = ['activo', 'nivel_acceso']
    search_fields = ['codigo', 'nombre']
    ordering = ['orden', 'nombre']


@admin.register(TipoFuncionario)
class TipoFuncionarioAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'activo', 'orden']
    list_filter = ['activo']
    search_fields = ['codigo', 'nombre']
    ordering = ['orden', 'nombre']


@admin.register(EstadoRegistroAsistencia)
class EstadoRegistroAsistenciaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'cuenta_como_asistencia', 'requiere_justificacion', 'color_hex', 'orden']
    list_filter = ['cuenta_como_asistencia', 'requiere_justificacion', 'activo']
    search_fields = ['codigo', 'nombre']
    ordering = ['orden', 'nombre']


@admin.register(EstadoSolicitudPermiso)
class EstadoSolicitudPermisoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'es_terminal', 'permite_edicion', 'color_hex', 'orden']
    list_filter = ['es_terminal', 'permite_edicion', 'activo']
    search_fields = ['codigo', 'nombre']
    ordering = ['orden', 'nombre']


@admin.register(TipoEquipo)
class TipoEquipoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'activo', 'orden']
    list_filter = ['activo']
    search_fields = ['codigo', 'nombre']
    ordering = ['orden', 'nombre']


@admin.register(EstadoEquipo)
class EstadoEquipoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'disponible_prestamo', 'color_hex', 'orden']
    list_filter = ['disponible_prestamo', 'activo']
    search_fields = ['codigo', 'nombre']
    ordering = ['orden', 'nombre']


@admin.register(PeriodoLiquidacion)
class PeriodoLiquidacionAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'fecha_inicio', 'fecha_termino', 'activo', 'cerrado']
    list_filter = ['activo', 'cerrado', 'anio']
    search_fields = ['mes', 'anio']
    ordering = ['-anio', '-mes']


@admin.register(JornadaLaboral)
class JornadaLaboralAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'horas', 'activo', 'orden']
    list_filter = ['activo']
    search_fields = ['codigo', 'nombre']
    ordering = ['orden', 'nombre']


@admin.register(TipoDia)
class TipoDiaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'cuenta_como_asistencia', 'descuenta_dias', 'color_hex', 'orden']
    list_filter = ['cuenta_como_asistencia', 'descuenta_dias', 'activo']
    search_fields = ['codigo', 'nombre']
    ordering = ['orden', 'nombre']

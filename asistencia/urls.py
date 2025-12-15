from django.urls import path
from .views import (
    GestionHorariosView,
    MiAsistenciaView,
    CargaHorariosView,
    GestionAsistenciaView,
    CargaRegistrosAsistenciaView,
    DescargarAsistenciaView,
    CrearHorarioView,
    EditarHorarioView,
    ToggleHorarioView,
    DetalleUsuarioAsistenciaView,
    EliminarRegistroAsistenciaView,
    EliminarTodosRegistrosUsuarioView,
    EliminarTodasAsistenciasView,
    RecalcularEstadoAsistenciaView,
    ReporteAsistenciaMensualView,
    ReporteAsistenciaIndividualView,
    CrearAlegacionView,
    GestionAlegacionesView,
    RevisarAlegacionView,
    GestionDiasFestivosView,
    CrearDiaFestivoView,
    EliminarDiaFestivoView,
    JustificarRegistroView,
)

app_name = 'asistencia'

urlpatterns = [
    # Gestión de horarios
    path("horarios/", GestionHorariosView.as_view(), name="gestion_horarios"),
    path("cargar-horarios/", CargaHorariosView.as_view(), name="carga_horarios"),
    path("horario/crear/<int:funcionario_id>/", CrearHorarioView.as_view(), name="crear_horario"),
    path("horario/editar/<int:pk>/", EditarHorarioView.as_view(), name="editar_horario"),
    path("horario/toggle/<int:pk>/", ToggleHorarioView.as_view(), name="toggle_horario"),

    # Gestión de asistencia
    path("gestion/", GestionAsistenciaView.as_view(), name="gestion_asistencia"),
    path("usuario/<int:user_id>/", DetalleUsuarioAsistenciaView.as_view(), name="detalle_usuario"),
    path("registro/<int:pk>/eliminar/", EliminarRegistroAsistenciaView.as_view(), name="eliminar_registro"),
    path("usuario/<int:user_id>/eliminar-todos/", EliminarTodosRegistrosUsuarioView.as_view(), name="eliminar_todos_registros"),
    path("cargar-registros/", CargaRegistrosAsistenciaView.as_view(), name="carga_registros"),
    path("descargar/", DescargarAsistenciaView.as_view(), name="descargar_asistencia"),

    # Vista personal
    path("mi-asistencia/", MiAsistenciaView.as_view(), name="mi_asistencia"),
    path("recalcular-estado/", RecalcularEstadoAsistenciaView.as_view(), name="recalcular_estado"),

    # Eliminación masiva
    path("eliminar-todas-asistencias/", EliminarTodasAsistenciasView.as_view(), name="eliminar_todas_asistencias"),

    # Reportes PDF
    path("reporte-mensual/", ReporteAsistenciaMensualView.as_view(), name="reporte_asistencia_mensual"),
    path("reporte-mensual/<int:anio>/<int:mes>/", ReporteAsistenciaMensualView.as_view(), name="reporte_asistencia_mensual_params"),
    path("reporte-individual/<int:anio>/<int:mes>/", ReporteAsistenciaIndividualView.as_view(), name="reporte_asistencia_individual"),

    # Alegaciones
    path("crear-alegacion/", CrearAlegacionView.as_view(), name="crear_alegacion"),
    path("gestion-alegaciones/", GestionAlegacionesView.as_view(), name="gestion_alegaciones"),
    path("revisar-alegacion/<int:pk>/", RevisarAlegacionView.as_view(), name="revisar_alegacion"),

    # Días festivos
    path("gestion-festivos/", GestionDiasFestivosView.as_view(), name="gestion_festivos"),
    path("crear-festivo/", CrearDiaFestivoView.as_view(), name="crear_festivo"),
    path("eliminar-festivo/<int:pk>/", EliminarDiaFestivoView.as_view(), name="eliminar_festivo"),

    # Justificaciones manuales
    path("justificar-registro/<int:pk>/", JustificarRegistroView.as_view(), name="justificar_registro"),
]
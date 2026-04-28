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
    EditarRegistroAsistenciaView,
    ExportarRetrasosExcelView,
    ExportarRetrasosPDFView,
    RecalcularTodaAsistenciaView,
    GestionAnoEscolarView,
    GuardarHorarioSemanalView,
    RecalcularAsistenciaUsuarioView,
    GestionHorariosExcepcionalesView,
    CrearHorarioExcepcionalView,
    EliminarHorarioExcepcionalView,
)

app_name = 'asistencia'

urlpatterns = [
    # Gestión de horarios
    path("horarios/", GestionHorariosView.as_view(), name="gestion_horarios"),
    path("cargar-horarios/", CargaHorariosView.as_view(), name="carga_horarios"),
    path("horario/crear/<int:funcionario_id>/", CrearHorarioView.as_view(), name="crear_horario"),
    path("horario/editar/<int:pk>/", EditarHorarioView.as_view(), name="editar_horario"),
    path("horario/toggle/<int:pk>/", ToggleHorarioView.as_view(), name="toggle_horario"),
    path("horario/guardar-semanal/<int:user_id>/", GuardarHorarioSemanalView.as_view(), name="guardar_horario_semanal"),

    # Gestión de asistencia
    path("gestion/", GestionAsistenciaView.as_view(), name="gestion_asistencia"),
    path("usuario/<int:user_id>/", DetalleUsuarioAsistenciaView.as_view(), name="detalle_usuario"),
    path("registro/<int:pk>/eliminar/", EliminarRegistroAsistenciaView.as_view(), name="eliminar_registro"),
    path("usuario/<int:user_id>/recalcular/", RecalcularAsistenciaUsuarioView.as_view(), name="recalcular_asistencia_usuario"),
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

    # Año escolar
    path("gestion-ano-escolar/", GestionAnoEscolarView.as_view(), name="gestion_ano_escolar"),

    # Justificaciones manuales
    path("justificar-registro/<int:pk>/", JustificarRegistroView.as_view(), name="justificar_registro"),
    path("registro/editar/<int:pk>/", EditarRegistroAsistenciaView.as_view(), name="editar_registro_asistencia"),

    # Exportar retrasos
    path("exportar-retrasos/excel/", ExportarRetrasosExcelView.as_view(), name="exportar_retrasos_excel"),
    path("exportar-retrasos/excel/<int:user_id>/", ExportarRetrasosExcelView.as_view(), name="exportar_retrasos_excel_individual"),
    path("exportar-retrasos/pdf/", ExportarRetrasosPDFView.as_view(), name="exportar_retrasos_pdf"),
    path("exportar-retrasos/pdf/<int:user_id>/", ExportarRetrasosPDFView.as_view(), name="exportar_retrasos_pdf_individual"),

    # Recálculo masivo
    path("recalcular-toda/", RecalcularTodaAsistenciaView.as_view(), name="recalcular_toda_asistencia"),

    # Horarios excepcionales
    path("excepcionales/", GestionHorariosExcepcionalesView.as_view(), name="gestion_excepcionales"),
    path("excepcionales/crear/", CrearHorarioExcepcionalView.as_view(), name="crear_excepcional"),
    path("excepcionales/<int:pk>/eliminar/", EliminarHorarioExcepcionalView.as_view(), name="eliminar_excepcional"),
]
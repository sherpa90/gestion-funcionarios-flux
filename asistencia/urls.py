from django.urls import path
from .views import (
    GestionHorariosView,
    RecalcularEstadoAsistenciaView,
    RecalcularTodaAsistenciaView,
    RecalcularAsistenciaUsuarioView,
    ReporteAsistenciaIndividualView,
    ExportarRetrasosExcelView,
    ExportarRetrasosPDFView,
    GestionAnoEscolarView,
    GuardarHorarioSemanalView,
    GestionHorariosExcepcionalesView,
    CrearHorarioExcepcionalView,
    EliminarHorarioExcepcionalView,
    ReporteAsistenciaAdministrativaView,
    ReporteAsistenciaAdministrativaExcelView,
    ReporteDAEM3View,
    ReporteDAEM3ExcelView,
    ReporteAsistenciaMensualExcelView,
)

app_name = 'asistencia'

urlpatterns = [
    # Gestión de horarios
    path("horarios/", GestionHorariosView.as_view(), name="gestion_horarios"),
    path("horario/guardar-semanal/<int:user_id>/", GuardarHorarioSemanalView.as_view(), name="guardar_horario_semanal"),

    # Gestión de asistencia
    path("usuario/<int:user_id>/recalcular/", RecalcularAsistenciaUsuarioView.as_view(), name="recalcular_asistencia_usuario"),

    # Vista personal
    path("recalcular-estado/", RecalcularEstadoAsistenciaView.as_view(), name="recalcular_estado"),

    # Reportes PDF
    path("reporte-administrativo/", ReporteAsistenciaAdministrativaView.as_view(), name="reporte_asistencia_administrativo"),
    path("reporte-administrativo/<int:anio>/<int:mes>/", ReporteAsistenciaAdministrativaView.as_view(), name="reporte_asistencia_administrativo_params"),
    path("reporte-administrativo-excel/", ReporteAsistenciaAdministrativaExcelView.as_view(), name="reporte_asistencia_administrativo_excel"),
    path("reporte-daem3/", ReporteDAEM3View.as_view(), name="reporte_daem3"),
    path("reporte-daem3-excel/", ReporteDAEM3ExcelView.as_view(), name="reporte_daem3_excel"),
    path("reporte-mensual-excel/", ReporteAsistenciaMensualExcelView.as_view(), name="reporte_asistencia_mensual_excel"),
    path("reporte-mensual-excel/<int:anio>/<int:mes>/", ReporteAsistenciaMensualExcelView.as_view(), name="reporte_asistencia_mensual_excel_params"),
    path("reporte-individual/<int:anio>/<int:mes>/", ReporteAsistenciaIndividualView.as_view(), name="reporte_asistencia_individual"),

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

    # Año escolar
    path("gestion-ano-escolar/", GestionAnoEscolarView.as_view(), name="gestion_ano_escolar"),
]
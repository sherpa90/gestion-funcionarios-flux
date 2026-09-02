from django.urls import path
from .views import (
    ReportesView, PDFIndividualView, PDFColectivoView, ExportarExcelView,
    ReporteMensualDiasAdministrativosView, ReporteMensualDiasAdministrativosExcelView,
    ExportarDAEMExcelView, ExportarDAEMPDFView, MiReportePDFView,
    ExportarHorariosExcelView, ExportarHorariosPDFView, MiHorarioPDFView,
    ExportarHorarioIndividualPDFView, ExportarJustificacionesExcelView, ExportarJustificacionesPDFView,
    ExportarCLAExcelView, ExportarCLAPDFView
)

urlpatterns = [
    path('', ReportesView.as_view(), name='reportes'),
    path('pdf/mi-reporte/', MiReportePDFView.as_view(), name='mi_reporte_pdf'),
    path('pdf/individual/<int:usuario_id>/', PDFIndividualView.as_view(), name='reportes_pdf_individual'),
    path('pdf/colectivo/', PDFColectivoView.as_view(), name='reportes_pdf_colectivo'),
    path('pdf/mensual/dias-administrativos/', ReporteMensualDiasAdministrativosView.as_view(), name='reportes_mensual_dias_administrativos'),
    path('excel/mensual/dias-administrativos/', ReporteMensualDiasAdministrativosExcelView.as_view(), name='reportes_mensual_dias_administrativos_excel'),
    path('excel/', ExportarExcelView.as_view(), name='reportes_excel'),
    path('daem-excel/', ExportarDAEMExcelView.as_view(), name='reportes_daem_excel'),
    path('daem-pdf/', ExportarDAEMPDFView.as_view(), name='reportes_daem_pdf'),
    path('excel/horarios/', ExportarHorariosExcelView.as_view(), name='exportar_horarios'),
    path('pdf/horarios/<int:usuario_id>/', ExportarHorarioIndividualPDFView.as_view(), name='exportar_horario_individual_pdf'),
    path('pdf/horarios/', ExportarHorariosPDFView.as_view(), name='exportar_horarios_pdf'),
    path('pdf/mi-horario/', MiHorarioPDFView.as_view(), name='mi_horario_pdf'),
    path('excel/justificaciones/', ExportarJustificacionesExcelView.as_view(), name='reportes_justificaciones_excel'),
    path('pdf/justificaciones/', ExportarJustificacionesPDFView.as_view(), name='reportes_justificaciones_pdf'),
    path('cla-excel/', ExportarCLAExcelView.as_view(), name='reportes_cla_excel'),
    path('cla-pdf/', ExportarCLAPDFView.as_view(), name='reportes_cla_pdf'),
    ]


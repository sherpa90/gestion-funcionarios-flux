from django.urls import path
from .views import ReportesView, PDFIndividualView, PDFColectivoView, ExportarExcelView, ReporteMensualDiasAdministrativosView, ExportarDAEMExcelView, MiReportePDFView

urlpatterns = [
    path('', ReportesView.as_view(), name='reportes'),
    path('pdf/mi-reporte/', MiReportePDFView.as_view(), name='mi_reporte_pdf'),
    path('pdf/individual/<int:usuario_id>/', PDFIndividualView.as_view(), name='reportes_pdf_individual'),
    path('pdf/colectivo/', PDFColectivoView.as_view(), name='reportes_pdf_colectivo'),
    path('pdf/mensual/dias-administrativos/', ReporteMensualDiasAdministrativosView.as_view(), name='reportes_mensual_dias_administrativos'),
    path('excel/', ExportarExcelView.as_view(), name='reportes_excel'),
    path('daem-excel/', ExportarDAEMExcelView.as_view(), name='reportes_daem_excel'),
]

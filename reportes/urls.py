from django.urls import path
from .views import ReportesView, PDFIndividualView, PDFColectivoView, ExportarExcelView, ReporteMensualDiasAdministrativosView

urlpatterns = [
    path('', ReportesView.as_view(), name='reportes'),
    path('pdf/individual/<int:usuario_id>/', PDFIndividualView.as_view(), name='reportes_pdf_individual'),
    path('pdf/colectivo/', PDFColectivoView.as_view(), name='reportes_pdf_colectivo'),
    path('pdf/mensual/dias-administrativos/', ReporteMensualDiasAdministrativosView.as_view(), name='reportes_mensual_dias_administrativos'),
    path('excel/', ExportarExcelView.as_view(), name='reportes_excel'),
]

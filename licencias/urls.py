from django.urls import path
from .views import LicenciaCreateView, LicenciaListView, LicenciaAdminListView, LicenciaUpdateView, LicenciaDeleteView

urlpatterns = [
    path('subir/', LicenciaCreateView.as_view(), name='subir_licencia'),
    path('mis-licencias/', LicenciaListView.as_view(), name='licencia_list'),
    path('admin/', LicenciaAdminListView.as_view(), name='licencia_admin_list'),
    path('admin/<int:pk>/editar/', LicenciaUpdateView.as_view(), name='licencia_edit'),
    path('admin/<int:pk>/eliminar/', LicenciaDeleteView.as_view(), name='licencia_delete'),
]

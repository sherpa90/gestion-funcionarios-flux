from django.urls import path
from .views import (
    SolicitudCreateView, SolicitudListView, SolicitudDirectorDashboardView,
    SolicitudAdminListView, SolicitudActionView, SolicitudBypassView,
    SolicitudAdminManagementView, SolicitudAdminEditView, SolicitudAdminDeleteView
)

urlpatterns = [
    path('solicitar/', SolicitudCreateView.as_view(), name='solicitar_permiso'),
    path('ingresar-directo/', SolicitudBypassView.as_view(), name='solicitud_bypass'),
    path('mis-solicitudes/', SolicitudListView.as_view(), name='dashboard_funcionario'),
    path('gestion/', SolicitudDirectorDashboardView.as_view(), name='dashboard_director'), # Dashboard con días disponibles
    path('gestion/admin/', SolicitudAdminListView.as_view(), name='solicitudes_admin'),
    path('admin/gestion/', SolicitudAdminManagementView.as_view(), name='admin_management'),
    path('admin/editar/<int:pk>/', SolicitudAdminEditView.as_view(), name='admin_edit_solicitud'),
    path('admin/eliminar/<int:pk>/', SolicitudAdminDeleteView.as_view(), name='admin_delete_solicitud'),
    path('accion/<int:pk>/<str:action>/', SolicitudActionView.as_view(), name='solicitud_action'),
]

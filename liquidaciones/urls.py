from django.urls import path
from .views import (
    CargaLiquidacionesView,
    MisLiquidacionesView,
    DescargarTodasLiquidacionesView,
    DescargarLiquidacionesAnioView,
    GestionLiquidacionesView,
    AdminLiquidacionesOverviewView,
    AdminFuncionarioLiquidacionesView,
    AdminEliminarLiquidacionView
)

urlpatterns = [
    path('carga/', CargaLiquidacionesView.as_view(), name='carga_liquidaciones'),
    path('mis-liquidaciones/', MisLiquidacionesView.as_view(), name='mis_liquidaciones'),
    path('descargar-todas/', DescargarTodasLiquidacionesView.as_view(), name='descargar_todas_liquidaciones'),
    path('descargar-anio/<int:anio>/', DescargarLiquidacionesAnioView.as_view(), name='descargar_liquidaciones_anio'),
    path('gestion/', GestionLiquidacionesView.as_view(), name='gestion_liquidaciones'),
    # Vistas administrativas para gestión de liquidaciones
    path('admin/overview/', AdminLiquidacionesOverviewView.as_view(), name='admin_liquidaciones_overview'),
    path('admin/funcionario/<int:funcionario_id>/', AdminFuncionarioLiquidacionesView.as_view(), name='admin_funcionario_liquidaciones'),
    path('admin/eliminar-liquidacion/<int:liquidacion_id>/', AdminEliminarLiquidacionView.as_view(), name='admin_eliminar_liquidacion'),
]

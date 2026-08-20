from django.urls import path
from . import views

urlpatterns = [
    # Inventario
    path('inventario/', views.inventario_equipos, name='inventario_equipos'),
    path('crear/', views.crear_equipo, name='crear_equipo'),
    path('editar/<int:equipo_id>/', views.editar_equipo, name='editar_equipo'),
    path('eliminar/<int:equipo_id>/', views.eliminar_equipo, name='eliminar_equipo'),
    path('exportar/excel/', views.export_inventario_excel, name='export_inventario_excel'),
    path('exportar/pdf/', views.export_inventario_pdf, name='export_inventario_pdf'),
    path('lugares/crear/', views.crear_lugar_equipo, name='crear_lugar_equipo'),
    path('lugares/editar/<int:lugar_id>/', views.editar_lugar_equipo, name='editar_lugar_equipo'),
    path('lugares/eliminar/<int:lugar_id>/', views.eliminar_lugar_equipo, name='eliminar_lugar_equipo'),
    path('detalle/<int:equipo_id>/', views.detalle_equipo, name='detalle_equipo'),
    path('detalle/<int:equipo_id>/hito/agregar/', views.agregar_hito, name='agregar_hito'),

    # Asignaciones y Préstamos
    path('lista/', views.lista_equipos, name='lista_equipos'),
    path('asignar/<int:equipo_id>/', views.asignar_equipo, name='asignar_equipo'),
    path('devolver/<int:prestamo_id>/', views.devolver_equipo, name='devolver_equipo'),
    path('reporte/pdf/', views.reporte_prestamos_pdf, name='reporte_prestamos_pdf'),
    path('reporte/pdf/<int:usuario_id>/', views.reporte_prestamos_pdf, name='reporte_prestamos_pdf'),

    # Préstamos Diarios
    path('prestamos-diarios/', views.prestamos_diarios, name='prestamos_diarios'),
    path('prestamos-diarios/crear/', views.crear_prestamo_diario, name='crear_prestamo_diario'),
    path('prestamos-diarios/terminar/<int:prestamo_id>/', views.terminar_prestamo_diario, name='terminar_prestamo_diario'),
    path('prestamos-diarios/reporte/pdf/', views.reporte_prestamos_diarios_pdf, name='reporte_prestamos_diarios_pdf'),

    # Tickets y Bitácora General TI / Gestión de Fallas
    path('gestion-fallas/', views.gestion_tickets_bitacora, name='gestion_fallas'),
    path('tickets/', views.gestion_tickets_bitacora, name='gestion_tickets_bitacora'),
    path('tickets/crear/', views.crear_ticket_bitacora, name='crear_ticket_bitacora'),
    path('tickets/editar/<int:ticket_id>/', views.editar_ticket_bitacora, name='editar_ticket_bitacora'),
    path('tickets/eliminar/<int:ticket_id>/', views.eliminar_ticket_bitacora, name='eliminar_ticket_bitacora'),
    path('tickets/reporte/pdf/', views.reporte_bitacora_pdf, name='reporte_bitacora_pdf'),
    path('falla/actualizar/<int:falla_id>/', views.actualizar_estado_falla, name='actualizar_estado_falla'),
    path('falla/reportar/<int:equipo_id>/', views.reportar_falla, name='reportar_falla'),

    # Funcionario
    path('mis-equipos/', views.mis_equipos, name='mis_equipos'),
]

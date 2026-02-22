from django.urls import path
from . import views

urlpatterns = [
    # Administrador
    path('lista/', views.lista_equipos, name='lista_equipos'),
    path('crear/', views.crear_equipo, name='crear_equipo'),
    path('editar/<int:equipo_id>/', views.editar_equipo, name='editar_equipo'),
    path('eliminar/<int:equipo_id>/', views.eliminar_equipo, name='eliminar_equipo'),
    path('asignar/<int:equipo_id>/', views.asignar_equipo, name='asignar_equipo'),
    path('devolver/<int:prestamo_id>/', views.devolver_equipo, name='devolver_equipo'),
    path('reporte/pdf/', views.reporte_prestamos_pdf, name='reporte_prestamos_pdf'),
    path('reporte/pdf/<int:usuario_id>/', views.reporte_prestamos_pdf, name='reporte_prestamos_pdf'),
    
    
    # Gestión de Fallas
    path('gestion-fallas/', views.gestion_fallas, name='gestion_fallas'),
    path('falla/actualizar/<int:falla_id>/', views.actualizar_estado_falla, name='actualizar_estado_falla'),
    path('falla/reportar/<int:equipo_id>/', views.reportar_falla, name='reportar_falla'),

    # Funcionario
    path('mis-equipos/', views.mis_equipos, name='mis_equipos'),
]

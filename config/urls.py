from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.http import HttpResponseRedirect, Http404
import os
from core.views import CustomLoginView, DashboardView, HealthCheckView
from django.contrib.auth.views import LogoutView


def serve_media(request, path):
    """
    Vista personalizada para servir archivos media en produccion.
    Esta vista es necesaria porque en production (DEBUG=False), Django no sirve
    archivos media automaticamente y nginx de Dokploy no esta configurado para /media/
    """
    from django.http import FileResponse, Http404
    import os
    import time
    
    # Seguridad: evitar path traversal
    # El path no debe contener ../ o empezar con /
    if '..' in path or path.startswith('/'):
        raise Http404("Invalid path")
    
    # Construir la ruta completa del archivo
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    
    # Verificar que el archivo existe y esta dentro de MEDIA_ROOT
    # Agregar reintentos por si el archivo se esta escribiendo
    max_attempts = 3
    for attempt in range(max_attempts):
        if os.path.exists(file_path):
            break
        time.sleep(0.1)  # Esperar 100ms entre intentos
    
    if not os.path.exists(file_path):
        raise Http404("File not found")
    
    # Verificar que el archivo esta dentro del directorio media
    real_path = os.path.realpath(file_path)
    real_media_root = os.path.realpath(settings.MEDIA_ROOT)
    
    if not real_path.startswith(real_media_root):
        raise Http404("Access denied")
    
    # Verificar que el archivo es legible
    if not os.access(file_path, os.R_OK):
        raise Http404("File not readable")
    
    # Determinar el tipo de contenido basado en la extension
    if path.lower().endswith('.pdf'):
        content_type = 'application/pdf'
    elif path.lower().endswith(('.jpg', '.jpeg')):
        content_type = 'image/jpeg'
    elif path.lower().endswith('.png'):
        content_type = 'image/png'
    elif path.lower().endswith('.gif'):
        content_type = 'image/gif'
    elif path.lower().endswith('.svg'):
        content_type = 'image/svg+xml'
    elif path.lower().endswith('.doc'):
        content_type = 'application/msword'
    elif path.lower().endswith('.docx'):
        content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif path.lower().endswith('.xls'):
        content_type = 'application/vnd.ms-excel'
    elif path.lower().endswith('.xlsx'):
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    else:
        content_type = 'application/octet-stream'
    
    # Abrir el archivo y crear la respuesta
    # FileResponse cierra automaticamente el archivo al final
    try:
        response = FileResponse(
            open(file_path, 'rb'),
            content_type=content_type,
            as_attachment=False
        )
        # Agregar headers para evitar cache de nginx
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['Content-Disposition'] = 'inline; filename=' + os.path.basename(path)
        return response
    except Exception:
        raise Http404("Error reading file")


urlpatterns = [
    path('', lambda request: redirect('login')),
    path('admin/', admin.site.urls),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('permisos/', include('permisos.urls')),
    path('licencias/', include('licencias.urls')),
    path('reportes/', include('reportes.urls')),
    path('liquidaciones/', include('liquidaciones.urls')),
    path('equipos/', include('equipos.urls')),
    path('usuarios/', include('users.urls')),
    path('dashboard/admin/', include('admin_dashboard.urls')),
    path('asistencia/', include('asistencia.urls')),

    # Health checks and monitoring
    path('health/', HealthCheckView.as_view(), name='health_check'),

    # Servir archivos media en produccion
    # Necesario porque nginx de Dokploy no esta configurado para servir /media/
    path('media/<path:path>', serve_media, name='media'),
]

# En desarrollo, usar la configuracion estatica de Django
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

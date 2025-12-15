from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from core.views import CustomLoginView, DashboardView, HealthCheckView
from django.contrib.auth.views import LogoutView

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
    path('usuarios/', include('users.urls')),
    path('dashboard/admin/', include('admin_dashboard.urls')),
    path('asistencia/', include('asistencia.urls')),

    # Health checks and monitoring
    path('health/', HealthCheckView.as_view(), name='health_check'),
]

# Servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

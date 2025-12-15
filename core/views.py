from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db import connection
from django.core.files.storage import default_storage
from django.conf import settings
import psutil
import os
from datetime import datetime

class CustomLoginView(LoginView):
    template_name = 'core/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('dashboard')

class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        if user.role == 'ADMIN':
            # Administradores van al dashboard de funcionarios para ver días y solicitar permisos
            return redirect('dashboard_funcionario')
        elif user.role == 'DIRECTOR':
            return redirect('dashboard_director')
        else:
            return redirect('dashboard_funcionario')


class HealthCheckView(View):
    """
    Health check endpoint con métricas detalladas del sistema.
    Usado por load balancers, monitoring tools y orquestadores.
    """

    def get(self, request):
        """
        Retorna estado del sistema y métricas básicas.
        """
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'sgpal',
            'version': '1.0.0',
        }

        # Database health check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_data['database'] = {'status': 'healthy', 'response_time_ms': 0}
        except Exception as e:
            health_data['database'] = {'status': 'unhealthy', 'error': str(e)}
            health_data['status'] = 'unhealthy'

        # Storage health check
        try:
            # Verificar que podemos escribir en media directory
            test_file = os.path.join(settings.MEDIA_ROOT, '.health_check')
            with open(test_file, 'w') as f:
                f.write('health_check')
            os.remove(test_file)
            health_data['storage'] = {'status': 'healthy'}
        except Exception as e:
            health_data['storage'] = {'status': 'unhealthy', 'error': str(e)}
            health_data['status'] = 'unhealthy'

        # System metrics
        try:
            health_data['system'] = {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory': {
                    'total': psutil.virtual_memory().total,
                    'available': psutil.virtual_memory().available,
                    'percent': psutil.virtual_memory().percent,
                },
                'disk': {
                    'total': psutil.disk_usage('/').total,
                    'free': psutil.disk_usage('/').free,
                    'percent': psutil.disk_usage('/').percent,
                }
            }
        except Exception as e:
            health_data['system'] = {'status': 'error', 'error': str(e)}

        # Application metrics
        try:
            from users.models import CustomUser
            from liquidaciones.models import Liquidacion
            from permisos.models import SolicitudPermiso

            health_data['metrics'] = {
                'users': {
                    'total': CustomUser.objects.count(),
                    'active_today': CustomUser.objects.filter(
                        last_login__date=datetime.now().date()
                    ).count()
                },
                'payrolls': {
                    'total': Liquidacion.objects.count(),
                    'this_month': Liquidacion.objects.filter(
                        mes=datetime.now().month,
                        anio=datetime.now().year
                    ).count()
                },
                'permissions': {
                    'total': SolicitudPermiso.objects.count(),
                    'pending': SolicitudPermiso.objects.filter(estado='PENDIENTE').count()
                }
            }
        except Exception as e:
            health_data['metrics'] = {'status': 'error', 'error': str(e)}

        # Return appropriate HTTP status
        status_code = 200 if health_data['status'] == 'healthy' else 503

        return JsonResponse(health_data, status=status_code)

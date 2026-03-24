from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db import connection
from django.core.files.storage import default_storage
from django.conf import settings
from django.contrib import messages
import psutil
import os
from datetime import datetime

class CustomLoginView(LoginView):
    template_name = 'core/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('dashboard')
    
    def form_invalid(self, form):
        # Verificar si el usuario está bloqueado o cerca del límite de intentos
        username = form.cleaned_data.get('username')
        if username:
            from django.contrib.auth import get_user_model
            try:
                from axes.helpers import get_request_attempt_count, get_max_login_attempts
            except ImportError:
                # Para axes < 8.x
                from axes.helpers import get_failures, get_max_failures as get_max_login_attempts
                get_request_attempt_count = lambda request: len(get_failures(request))
            
            User = get_user_model()
            try:
                user = User.objects.get(email=username)
                
                # Caso 1: El usuario ya está bloqueado manualmente
                if user.is_blocked:
                    messages.error(self.request, 'Su cuenta ha sido bloqueada permanentemente. Por favor, contacte al administrador.')
                    return super().form_invalid(form)
                
                # Caso 2: El usuario está bloqueado por Axes (esto suele ser gestionado por el middleware, 
                # pero agregamos una advertencia si estamos cerca del límite)
                try:
                    failures_count = get_request_attempt_count(self.request)
                except Exception:
                    failures_count = 0
                    
                max_failures = get_max_login_attempts(self.request)
                
                if failures_count > 0:
                    remaining = max_failures - failures_count
                    if remaining > 0 and remaining <= 2:
                        messages.warning(
                            self.request, 
                            f'¡Cuidado! Te quedan solo {remaining} {"intento" if remaining == 1 else "intentos"} antes de que tu cuenta sea bloqueada temporalmente.'
                        )
                    elif remaining == 0:
                        messages.error(
                            self.request,
                            'Demasiados intentos fallidos. Su cuenta ha sido bloqueada temporalmente por seguridad.'
                        )
            except User.DoesNotExist:
                pass
                
        return super().form_invalid(form)

class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        if user.role == 'ADMIN':
            # Administradores van al dashboard de funcionarios para ver días y solicitar permisos
            return redirect('dashboard_funcionario')
        else:
            return redirect('dashboard_funcionario')


class HealthCheckView(View):
    """
    Health check endpoint con métricas detalladas del sistema.
    
    NOTA DE SEGURIDAD: Por defecto solo devuelve estado básico.
    Para métricas detalladas, configurar HEALTH_CHECK_DETAILED=True en producción.
    """

    def get(self, request):
        """
        Retorna estado del sistema y métricas básicas.
        """
        # Por defecto, solo devolver información básica para evitar exponer
        # información sensible del sistema en producción
        detailed_health = os.environ.get('HEALTH_CHECK_DETAILED', 'False').lower() in ('true', '1', 'yes', 'on')
        
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
            health_data['database'] = {'status': 'healthy'}
        except Exception as e:
            health_data['database'] = {'status': 'unhealthy', 'error': str(e)}
            health_data['status'] = 'unhealthy'

        # Only expose system metrics in detailed mode (development only)
        if detailed_health:
            # Storage health check
            try:
                test_file = os.path.join(settings.MEDIA_ROOT, '.health_check')
                with open(test_file, 'w') as f:
                    f.write('health_check')
                os.remove(test_file)
                health_data['storage'] = {'status': 'healthy'}
            except Exception as e:
                health_data['storage'] = {'status': 'unhealthy', 'error': str(e)}
                health_data['status'] = 'unhealthy'

            # System metrics - ONLY expose in detailed mode
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

            # Application metrics - ONLY expose in detailed mode
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

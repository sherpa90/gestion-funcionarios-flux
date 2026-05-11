from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.http import JsonResponse, FileResponse, Http404
from django.db import connection
from django.core.files.storage import default_storage
from django.conf import settings
from django.contrib import messages
import psutil
import os
from datetime import datetime
from licencias.models import LicenciaMedica
from liquidaciones.models import Liquidacion

class SecureFileDownloadView(LoginRequiredMixin, View):
    """
    Vista segura para descargar archivos encriptados (Ley N° 21.719).
    Desencripta el archivo al vuelo antes de enviarlo al cliente.
    """
    def get(self, request, document_type, pk):
        if document_type == 'licencia':
            obj = get_object_or_404(LicenciaMedica, pk=pk)
            # Solo el dueño o el admin/secretaria puede descargar
            if request.user != obj.usuario and request.user.role not in ['ADMIN', 'DIRECTOR', 'SECRETARIA']:
                raise Http404("No tienes permiso para ver este documento.")
        elif document_type == 'liquidacion':
            obj = get_object_or_404(Liquidacion, pk=pk)
            if request.user != obj.funcionario and request.user.role not in ['ADMIN', 'DIRECTOR', 'SECRETARIA']:
                raise Http404("No tienes permiso para ver este documento.")
        else:
            raise Http404("Tipo de documento inválido.")
            
        if not obj.archivo:
            raise Http404("El archivo no existe.")
            
        try:
            # Al llamar a open(), EncryptedFileSystemStorage lo desencripta al vuelo
            file_obj = obj.archivo.open()
            return FileResponse(file_obj, as_attachment=False, filename=os.path.basename(obj.archivo.name))
        except Exception as e:
            raise Http404(f"Error al desencriptar o leer el archivo: {str(e)}")

class CustomLoginView(LoginView):
    template_name = 'core/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('dashboard')
    
    def form_invalid(self, form):
        # Verificar si el usuario está bloqueado manualmente
        username = form.cleaned_data.get('username')
        if username:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(email=username)
                
                # El usuario ya está bloqueado manualmente
                if user.is_blocked:
                    messages.error(self.request, 'Su cuenta ha sido bloqueada permanentemente. Por favor, contacte al administrador.')
            except User.DoesNotExist:
                pass
            
            # Verificar intentos fallidos de Axes
            try:
                from axes.models import AccessAttempt
                limit = getattr(settings, 'AXES_FAILURE_LIMIT', 6)
                attempt = AccessAttempt.objects.filter(username__iexact=username).first()
                if attempt and attempt.failures_since_start > 0:
                    faltan = limit - attempt.failures_since_start
                    if faltan > 0:
                        messages.warning(self.request, f"Credenciales incorrectas. Te quedan {faltan} intentos antes del bloqueo de seguridad.")
            except Exception:
                pass
                
        return super().form_invalid(form)

class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
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

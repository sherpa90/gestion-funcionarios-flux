from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import timedelta

from users.models import CustomUser
from permisos.models import SolicitudPermiso
from licencias.models import LicenciaMedica
from .models import SystemLog
from .utils import registrar_log, get_client_ip


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'admin_dashboard/dashboard.html'
    
    def test_func(self):
        return self.request.user.role == 'ADMIN'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['total_usuarios'] = CustomUser.objects.count()
        context['total_funcionarios'] = CustomUser.objects.filter(role='FUNCIONARIO').count()
        context['total_directivos'] = CustomUser.objects.filter(
            role__in=['DIRECTOR', 'DIRECTIVO', 'SECRETARIA']
        ).count()
        
        context['solicitudes_pendientes'] = SolicitudPermiso.objects.filter(
            estado='PENDIENTE'
        ).count()
        context['solicitudes_aprobadas_mes'] = SolicitudPermiso.objects.filter(
            estado='APROBADO',
            updated_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Licencias activas: aquellas cuya fecha de inicio + días es mayor a hoy
        hoy = timezone.now().date()
        licencias_activas = 0
        for lic in LicenciaMedica.objects.all():
            fecha_termino = lic.fecha_inicio + timedelta(days=lic.dias)
            if lic.fecha_inicio <= hoy <= fecha_termino:
                licencias_activas += 1
        
        context['licencias_activas'] = licencias_activas
        context['licencias_mes'] = LicenciaMedica.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        context['logs_recientes'] = SystemLog.objects.select_related(
            'usuario'
        ).order_by('-timestamp')[:10]
        
        usuarios_stats = CustomUser.objects.filter(role='FUNCIONARIO').aggregate(
            total_disponibles=Sum('dias_disponibles'),
            total_usuarios=Count('id')
        )
        context['dias_totales_disponibles'] = usuarios_stats['total_disponibles'] or 0
        context['promedio_dias_disponibles'] = (
            (usuarios_stats['total_disponibles'] / usuarios_stats['total_usuarios'])
            if usuarios_stats['total_usuarios'] > 0 else 0
        )
        
        context['usuarios_saldo_bajo'] = CustomUser.objects.filter(
            role='FUNCIONARIO',
            dias_disponibles__lt=2.0
        ).count()
        
        context['chart_labels'], context['chart_data'] = self.get_weekly_chart_data()
        
        registrar_log(
            usuario=self.request.user,
            tipo='AUTH',
            accion='Acceso al Dashboard Admin',
            descripcion='Usuario accedió al panel de administración',
            ip_address=get_client_ip(self.request)
        )
        
        return context
    
    def get_weekly_chart_data(self):
        labels = []
        data = []
        
        for i in range(6, -1, -1):
            fecha = timezone.now().date() - timedelta(days=i)
            labels.append(fecha.strftime('%d/%m'))
            
            count = SolicitudPermiso.objects.filter(
                created_at__date=fecha
            ).count()
            data.append(count)
        
        return labels, data


class SystemLogsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Vista simple de logs del sistema - quién hizo qué"""
    template_name = 'admin_dashboard/logs.html'
    
    def test_func(self):
        return self.request.user.role == 'ADMIN'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener logs recientes (últimos 50)
        context['logs'] = SystemLog.objects.select_related('usuario').order_by('-timestamp')[:50]
        
        return context

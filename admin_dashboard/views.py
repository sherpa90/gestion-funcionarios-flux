from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta

from users.models import CustomUser
from permisos.models import SolicitudPermiso
from licencias.models import LicenciaMedica
from .models import SystemLog
from .utils import registrar_log, get_client_ip


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'admin_dashboard/dashboard.html'
    
    def test_func(self):
        # ADMIN, DIRECTOR, DIRECTIVO y SECRETARIA pueden acceder
        return self.request.user.role in ['ADMIN', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA']
    
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
        
        # Licencias activas: cálculo eficiente (compatible con todas las DB)
        hoy = timezone.now().date()
        
        # Obtener licencias activas (fecha inicio <= hoy <= fecha retorno)
        licencias_activas_list = []
        for lic in LicenciaMedica.objects.select_related('usuario').filter(fecha_inicio__lte=hoy):
            fecha_retorno = lic.fecha_inicio + timedelta(days=lic.dias)
            if fecha_retorno >= hoy:
                licencias_activas_list.append({
                    'usuario': lic.usuario,
                    'fecha_inicio': lic.fecha_inicio,
                    'dias': lic.dias,
                    'fecha_retorno': fecha_retorno,
                    'dias_restantes': fecha_retorno - hoy,
                })
        
        # Licencias que aún no comienzan (próximas)
        licencias_proximas_list = []
        for lic in LicenciaMedica.objects.select_related('usuario').filter(fecha_inicio__gt=hoy).order_by('fecha_inicio')[:5]:
            fecha_retorno = lic.fecha_inicio + timedelta(days=lic.dias)
            licencias_proximas_list.append({
                'usuario': lic.usuario,
                'fecha_inicio': lic.fecha_inicio,
                'dias': lic.dias,
                'fecha_retorno': fecha_retorno,
                'dias_para_iniciar': lic.fecha_inicio - hoy,
            })
        
        context['licencias_activas'] = len(licencias_activas_list)
        context['licencias_mes'] = LicenciaMedica.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Agregar licencias al contexto
        context['licencias_activas_detalle'] = licencias_activas_list
        context['licencias_proximas_detalle'] = licencias_proximas_list
        
        # Licencias por usuario para el año actual
        context['licencias_por_funcionario'] = self.get_licencias_por_funcionario()
        
        # Días administrativos activos y próximos
        context['dias_administrativos_activos'] = self.get_dias_administrativos_activos()
        context['proximos_dias_administrativos'] = self.get_proximos_dias_administrativos()
        
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
    
    def get_licencias_por_funcionario(self):
        """Obtiene resumen de licencias por funcionario para el año actual"""
        hoy = timezone.now().date()
        año_actual = hoy.year
        
        # Obtener todas las licencias del año actual
        licencias = LicenciaMedica.objects.filter(
            fecha_inicio__year=año_actual
        ).select_related('usuario').order_by('usuario__last_name')
        
        # Agrupar por usuario
        licencias_por_usuario = {}
        for lic in licencias:
            usuario_id = lic.usuario.id
            if usuario_id not in licencias_por_usuario:
                licencias_por_usuario[usuario_id] = {
                    'usuario': lic.usuario,
                    'total_dias': 0,
                    'licencias': []
                }
            licencias_por_usuario[usuario_id]['total_dias'] += lic.dias
            licencias_por_usuario[usuario_id]['licencias'].append({
                'fecha_inicio': lic.fecha_inicio,
                'dias': lic.dias,
                'fecha_retorno': lic.fecha_inicio + timedelta(days=lic.dias),
            })
        
        return sorted(licencias_por_usuario.values(), key=lambda x: x['usuario'].get_full_name())
    
    def get_dias_administrativos_activos(self):
        """Obtiene los funcionarios que actualmente están en día administrativo"""
        from permisos.models import SolicitudPermiso
        
        hoy = timezone.now().date()
        
        # Obtener permisos aprobados donde hoy está dentro del rango de fechas
        permisos_activos = SolicitudPermiso.objects.select_related('usuario').filter(
            estado='APROBADO',
            fecha_inicio__lte=hoy,
            fecha_termino__gte=hoy
        ).order_by('usuario__last_name')
        
        resultado = []
        for perm in permisos_activos:
            dias_restantes = (perm.fecha_termino - hoy).days + 1
            resultado.append({
                'usuario': perm.usuario,
                'fecha_inicio': perm.fecha_inicio,
                'fecha_termino': perm.fecha_termino,
                'dias_solicitados': perm.dias_solicitados,
                'jornada': perm.get_jornada_display(),
                'dias_restantes': dias_restantes,
            })
        
        return resultado
    
    def get_proximos_dias_administrativos(self):
        """Obtiene los permisos administrativos próximos (que aún no comienzan)"""
        from permisos.models import SolicitudPermiso
        
        hoy = timezone.now().date()
        
        # Obtener permisos aprobados que aún no comienzan
        permisos_proximos = SolicitudPermiso.objects.select_related('usuario').filter(
            estado='APROBADO',
            fecha_inicio__gt=hoy
        ).order_by('fecha_inicio')[:5]
        
        resultado = []
        for perm in permisos_proximos:
            dias_para_iniciar = (perm.fecha_inicio - hoy).days
            resultado.append({
                'usuario': perm.usuario,
                'fecha_inicio': perm.fecha_inicio,
                'fecha_termino': perm.fecha_termino,
                'dias_solicitados': perm.dias_solicitados,
                'jornada': perm.get_jornada_display(),
                'dias_para_iniciar': dias_para_iniciar,
            })
        
        return resultado
    
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


class BlockedUsersView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Vista para gestionar usuarios bloqueados"""
    template_name = 'admin_dashboard/blocked_users.html'
    
    def test_func(self):
        # Solo ADMIN puede gestionar usuarios bloqueados
        return self.request.user.role == 'ADMIN'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener todos los usuarios bloqueados manualmente
        manually_blocked = CustomUser.objects.filter(
            is_blocked=True
        ).select_related('blocked_by').order_by('-blocked_at')
        
        # Obtener usuarios bloqueados por Axes (intentos fallidos)
        axes_blocked_users = []
        try:
            from axes.models import AccessAttempt
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Obtener intentos de acceso bloqueados
            blocked_attempts = AccessAttempt.objects.filter(
                blocked=True
            ).order_by('-attempt_time')[:50]
            
            for attempt in blocked_attempts:
                username = attempt.username
                if username:
                    try:
                        user = User.objects.get(email__iexact=username)
                        axes_blocked_users.append({
                            'user': user,
                            'is_axes_blocked': True,
                            'blocked_at': attempt.attempt_time,
                            'ip_address': attempt.ip_address,
                            'attempts': attempt.failures_since_start
                        })
                    except User.DoesNotExist:
                        pass
        except Exception as e:
            # Si axes no está configurado correctamente, ignoramos
            pass
        
        context['blocked_users'] = manually_blocked
        context['axes_blocked_users'] = axes_blocked_users
        
        # Obtener usuarios no bloqueados para poder bloquear (todos los roles excepto ADMIN)
        context['active_users'] = CustomUser.objects.filter(
            is_blocked=False
        ).exclude(
            role='ADMIN'
        ).order_by('first_name', 'last_name')
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Manejar acciones de bloquear/desbloquear"""
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        
        if action == 'block':
            user = get_object_or_404(CustomUser, pk=user_id)
            user.is_blocked = True
            user.blocked_at = timezone.now()
            user.blocked_by = request.user
            user.save()
            
            messages.success(request, f'Usuario {user.get_full_name()} ha sido bloqueado.')
            
            registrar_log(
                usuario=request.user,
                tipo='USER',
                accion='Bloqueo de usuario',
                descripcion=f'Usuario {user.get_full_name()} (ID: {user.id}) fue bloqueado',
                ip_address=get_client_ip(request)
            )
            
        elif action == 'unblock':
            user = get_object_or_404(CustomUser, pk=user_id, is_blocked=True)
            user.is_blocked = False
            user.blocked_at = None
            user.blocked_by = None
            user.save()
            
            messages.success(request, f'Usuario {user.get_full_name()} ha sido desbloqueado.')
            
            registrar_log(
                usuario=request.user,
                tipo='USER',
                accion='Desbloqueo de usuario',
                descripcion=f'Usuario {user.get_full_name()} (ID: {user.id}) fue desbloqueado',
                ip_address=get_client_ip(request)
            )
        
        elif action == 'unblock_axes':
            # Desbloquear usuario de Axes
            try:
                from axes.helpers import clear_lockouts
                from axes.models import AccessAttempt
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                user = get_object_or_404(CustomUser, pk=user_id)
                
                # Buscar y eliminar los intentos de acceso bloqueados para este usuario
                AccessAttempt.objects.filter(
                    username__iexact=user.email
                ).delete()
                
                # También intentar desbloquear por IP si hay alguna
                try:
                    clear_lockouts(request)
                except:
                    pass
                
                messages.success(request, f'Usuario {user.get_full_name()} ha sido desbloqueado de Axes.')
                
                registrar_log(
                    usuario=request.user,
                    tipo='USER',
                    accion='Desbloqueo Axes',
                    descripcion=f'Usuario {user.get_full_name()} (ID: {user.id}) fue desbloqueado de Axes',
                    ip_address=get_client_ip(request)
                )
            except Exception as e:
                messages.error(request, f'Error al desbloquear de Axes: {str(e)}')
        
        return redirect('admin_dashboard:blocked_users')


class SystemLogsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Vista simple de logs del sistema - quién hizo qué"""
    template_name = 'admin_dashboard/logs.html'
    
    def test_func(self):
        # ADMIN, DIRECTOR, DIRECTIVO y SECRETARIA pueden ver los logs
        return self.request.user.role in ['ADMIN', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener logs recientes (últimos 50)
        context['logs'] = SystemLog.objects.select_related('usuario').order_by('-timestamp')[:50]
        
        return context

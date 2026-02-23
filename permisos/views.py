from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, ListView, View, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum
from .models import SolicitudPermiso
from .forms import SolicitudForm, SolicitudBypassForm
from users.models import CustomUser
from core.services import BusinessDayCalculator

class SolicitudCreateView(LoginRequiredMixin, CreateView):
    model = SolicitudPermiso
    form_class = SolicitudForm
    template_name = 'permisos/solicitud_form.html'
    success_url = reverse_lazy('dashboard_funcionario')

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        # Calcular fecha termino
        form.instance.fecha_termino = BusinessDayCalculator.calculate_end_date(
            form.instance.fecha_inicio,
            form.instance.dias_solicitados
        )

        # Validar saldo considerando solicitudes pendientes
        solicitudes_pendientes = SolicitudPermiso.objects.filter(
            usuario=self.request.user,
            estado='PENDIENTE'
        ).aggregate(total=Sum('dias_solicitados'))['total'] or 0.0
        
        saldo_real = self.request.user.dias_disponibles - solicitudes_pendientes

        if saldo_real < form.instance.dias_solicitados:
            form.add_error(None, f"Saldo insuficiente. Tienes {self.request.user.dias_disponibles} días disponibles, pero {solicitudes_pendientes} día(s) están en solicitudes pendientes de aprobación.")
            return self.form_invalid(form)

        # Auto-aprobar si el usuario es DIRECTOR
        if self.request.user.role == 'DIRECTOR':
            form.instance.estado = 'APROBADO'
            # Descontar días inmediatamente
            self.request.user.dias_disponibles -= form.instance.dias_solicitados
            self.request.user.save()
            messages.success(self.request, f'Solicitud aprobada automáticamente. Has utilizado {form.instance.dias_solicitados} días administrativos.')
        else:
            # Para otros roles, queda pendiente de aprobación
            form.instance.estado = 'PENDIENTE'
            messages.success(self.request, 'Solicitud enviada para aprobación del director.')

        return super().form_valid(form)

class SolicitudBypassView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Vista para que Secretaria ingrese permisos directamente (sin aprobación)"""
    model = SolicitudPermiso
    form_class = SolicitudBypassForm
    template_name = 'permisos/solicitud_bypass_form.html'
    success_url = reverse_lazy('solicitud_bypass')

    def test_func(self):
        return self.request.user.role in ['SECRETARIA', 'ADMIN']

    def form_valid(self, form):
        # Calcular fecha termino
        form.instance.fecha_termino = BusinessDayCalculator.calculate_end_date(
            form.instance.fecha_inicio, 
            form.instance.dias_solicitados
        )
        
        # Validar saldo considerando solicitudes pendientes
        usuario = form.instance.usuario
        solicitudes_pendientes = SolicitudPermiso.objects.filter(
            usuario=usuario,
            estado='PENDIENTE'
        ).aggregate(total=Sum('dias_solicitados'))['total'] or 0.0
        
        saldo_real = usuario.dias_disponibles - solicitudes_pendientes

        if saldo_real < form.instance.dias_solicitados:
            form.add_error(None, f"El usuario {usuario.get_full_name()} no tiene saldo suficiente. Saldo: {usuario.dias_disponibles} días, Pendiente: {solicitudes_pendientes} días.")
            return self.form_invalid(form)
        
        # Marcar como PENDIENTE (requiere aprobación del Director)
        form.instance.estado = 'PENDIENTE'
        form.instance.created_by = self.request.user  # Registrar quién creó la solicitud
        # No descontamos días aquí, se descuentan al aprobar
        
        messages.success(self.request, f'Solicitud registrada exitosamente para {usuario.get_full_name()}. Pendiente de aprobación por Director.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Mostrar solicitudes creadas por el usuario actual (Secretaria/Admin)
        # Incluye tanto solicitudes creadas como canceladas por el usuario actual
        solicitudes_creadas = SolicitudPermiso.objects.filter(created_by=self.request.user)
        solicitudes_canceladas = SolicitudPermiso.objects.filter(cancelled_by=self.request.user)

        # Combinar y ordenar por fecha de creación más reciente
        mis_ingresos = (solicitudes_creadas | solicitudes_canceladas).distinct().order_by('-created_at')[:10]
        context['mis_ingresos'] = mis_ingresos
        return context

class SolicitudListView(LoginRequiredMixin, ListView):
    model = SolicitudPermiso
    template_name = 'permisos/dashboard_funcionario.html'
    context_object_name = 'solicitudes'

    def get_queryset(self):
        return SolicitudPermiso.objects.filter(usuario=self.request.user).order_by('-created_at')[:5]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dias_disponibles'] = self.request.user.dias_disponibles
        context['dias_totales'] = 6.0  # Total de días administrativos por año
        return context

class SolicitudDirectorDashboardView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Dashboard para directores que incluye días disponibles y solicitudes pendientes"""
    model = SolicitudPermiso
    template_name = 'permisos/dashboard_director.html'
    context_object_name = 'solicitudes'

    def test_func(self):
        # DIRECTOR, DIRECTIVO y SECRETARIA pueden acceder
        return self.request.user.role in ['DIRECTOR', 'DIRECTIVO', 'SECRETARIA']

    def get_queryset(self):
        return SolicitudPermiso.objects.filter(estado='PENDIENTE').order_by('created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['historial'] = SolicitudPermiso.objects.exclude(estado='PENDIENTE').order_by('-updated_at')[:10]
        # Agregar información de días disponibles para directores
        context['dias_disponibles'] = self.request.user.dias_disponibles
        # Total de días administrativos por año (usar valor del usuario o valor por defecto)
        context['dias_totales'] = getattr(self.request.user, 'dias_totales', 6.0) or 6.0
        return context

class SolicitudAdminListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = SolicitudPermiso
    template_name = 'permisos/dashboard_director.html'
    context_object_name = 'solicitudes'

    def test_func(self):
        # DIRECTOR, DIRECTIVO y SECRETARIA pueden acceder
        return self.request.user.role in ['DIRECTOR', 'DIRECTIVO', 'SECRETARIA']

    def get_queryset(self):
        return SolicitudPermiso.objects.filter(estado='PENDIENTE').order_by('created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['historial'] = SolicitudPermiso.objects.exclude(estado='PENDIENTE').order_by('-updated_at')[:10]
        return context

class SolicitudActionView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.role in ['DIRECTOR', 'ADMIN', 'SECRETARIA']

    def post(self, request, pk, action):
        # Validate pk is a valid integer
        try:
            pk = int(pk)
        except (ValueError, TypeError):
            messages.error(request, 'Solicitud inválida.')
            return redirect('dashboard_director')
        
        # Validate action is a valid choice
        valid_actions = ['approve', 'reject', 'cancel']
        if action not in valid_actions:
            messages.error(request, 'Acción inválida.')
            return redirect('dashboard_director')
            
        solicitud = get_object_or_404(SolicitudPermiso, pk=pk)

        if action == 'approve':
            if solicitud.usuario.dias_disponibles >= solicitud.dias_solicitados:
                solicitud.estado = 'APROBADO'
                solicitud.usuario.dias_disponibles -= solicitud.dias_solicitados
                solicitud.usuario.save()
                solicitud.save()
                messages.success(request, 'Solicitud aprobada.')
            else:
                messages.error(request, 'El usuario no tiene saldo suficiente.')
        elif action == 'reject':
            solicitud.estado = 'RECHAZADO'
            solicitud.motivo_rechazo = request.POST.get('motivo_rechazo', '')
            solicitud.save()
            messages.success(request, 'Solicitud rechazada.')
        elif action == 'cancel':
            # Solo admins y secretarias pueden cancelar solicitudes aprobadas
            if request.user.role in ['ADMIN', 'SECRETARIA'] and solicitud.estado == 'APROBADO':
                solicitud.estado = 'CANCELADO'
                solicitud.motivo_cancelacion = request.POST.get('motivo_cancelacion', 'Cancelado por administrador')
                solicitud.cancelled_by = request.user
                solicitud.cancelled_at = timezone.now()
                # Devolver los días al usuario
                solicitud.usuario.dias_disponibles += solicitud.dias_solicitados
                solicitud.usuario.save()
                solicitud.save()
                messages.success(request, f'Solicitud cancelada. Se devolvieron {solicitud.dias_solicitados} días a {solicitud.usuario.get_full_name()}.')
            else:
                messages.error(request, 'No tienes permisos para cancelar esta solicitud.')

        return redirect('dashboard_director')


class SolicitudAdminManagementView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Vista administrativa completa para gestionar todas las solicitudes de permisos"""
    model = SolicitudPermiso
    template_name = 'permisos/admin_management.html'
    context_object_name = 'solicitudes'
    paginate_by = 25

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

    def get_queryset(self):
        queryset = SolicitudPermiso.objects.select_related('usuario', 'created_by', 'cancelled_by').order_by('-created_at')

        # Filtros
        usuario_id = self.request.GET.get('usuario')
        estado = self.request.GET.get('estado')
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        search = self.request.GET.get('search')

        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        if estado:
            queryset = queryset.filter(estado=estado)
        if fecha_desde:
            queryset = queryset.filter(fecha_inicio__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_inicio__lte=fecha_hasta)
        if search:
            queryset = queryset.filter(
                Q(usuario__first_name__icontains=search) |
                Q(usuario__last_name__icontains=search) |
                Q(observacion__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Usuarios para filtro
        context['usuarios'] = CustomUser.objects.filter(role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA']).order_by('last_name', 'first_name')

        # Estados para filtro
        context['estados'] = [
            ('PENDIENTE', 'Pendiente'),
            ('APROBADO', 'Aprobado'),
            ('RECHAZADO', 'Rechazado'),
            ('CANCELADO', 'Cancelado'),
        ]

        # Estadísticas
        total_solicitudes = SolicitudPermiso.objects.count()
        solicitudes_pendientes = SolicitudPermiso.objects.filter(estado='PENDIENTE').count()
        solicitudes_aprobadas = SolicitudPermiso.objects.filter(estado='APROBADO').count()
        solicitudes_rechazadas = SolicitudPermiso.objects.filter(estado='RECHAZADO').count()
        solicitudes_canceladas = SolicitudPermiso.objects.filter(estado='CANCELADO').count()

        context['estadisticas'] = {
            'total': total_solicitudes,
            'pendientes': solicitudes_pendientes,
            'aprobadas': solicitudes_aprobadas,
            'rechazadas': solicitudes_rechazadas,
            'canceladas': solicitudes_canceladas,
        }

        # Filtros aplicados
        context['filtros_aplicados'] = {
            'usuario': self.request.GET.get('usuario'),
            'estado': self.request.GET.get('estado'),
            'fecha_desde': self.request.GET.get('fecha_desde'),
            'fecha_hasta': self.request.GET.get('fecha_hasta'),
            'search': self.request.GET.get('search'),
        }

        return context


class SolicitudAdminEditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Vista para que admins/secretarias editen cualquier solicitud de permiso"""
    model = SolicitudPermiso
    form_class = SolicitudForm
    template_name = 'permisos/admin_edit.html'
    success_url = reverse_lazy('admin_management')

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # No limitar el queryset de usuarios - permitir editar cualquier usuario
        return kwargs

    def form_valid(self, form):
        # Guardar el estado anterior para comparar
        estado_anterior = self.object.estado
        dias_anteriores = self.object.dias_solicitados

        # Recalcular fecha término si cambió la fecha o días
        if 'fecha_inicio' in form.changed_data or 'dias_solicitados' in form.changed_data:
            form.instance.fecha_termino = BusinessDayCalculator.calculate_end_date(
                form.instance.fecha_inicio,
                form.instance.dias_solicitados
            )

        # Manejar cambios de estado que afectan el saldo de días
        nuevo_estado = form.cleaned_data.get('estado')

        # Si cambió de aprobado a otro estado, devolver días
        if estado_anterior == 'APROBADO' and nuevo_estado != 'APROBADO':
            form.instance.usuario.dias_disponibles += dias_anteriores
            form.instance.usuario.save()

        # Si cambió a aprobado desde otro estado, descontar días
        elif estado_anterior != 'APROBADO' and nuevo_estado == 'APROBADO':
            if form.instance.usuario.dias_disponibles >= form.instance.dias_solicitados:
                form.instance.usuario.dias_disponibles -= form.instance.dias_solicitados
                form.instance.usuario.save()
            else:
                form.add_error(None, f"El usuario no tiene suficientes días disponibles ({form.instance.usuario.dias_disponibles} disponibles, {form.instance.dias_solicitados} solicitados).")
                return self.form_invalid(form)

        # Actualizar el estado
        form.instance.estado = nuevo_estado

        # Registrar quién editó
        form.instance.updated_at = timezone.now()

        messages.success(self.request, f'Solicitud de {form.instance.usuario.get_full_name} actualizada exitosamente.')
        return super().form_valid(form)


class SolicitudAdminDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para que admins/secretarias cancelen solicitudes de permiso (devuelven días)"""
    template_name = 'permisos/admin_delete.html'

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

    def get(self, request, pk):
        solicitud = get_object_or_404(SolicitudPermiso, pk=pk)
        return render(request, self.template_name, {'solicitud': solicitud})

    def post(self, request, pk):
        solicitud = get_object_or_404(SolicitudPermiso, pk=pk)

        # Guardar el estado original antes de cambiarlo
        estado_original = solicitud.estado

        # Cambiar estado a CANCELADO en lugar de eliminar
        solicitud.estado = 'CANCELADO'
        solicitud.motivo_cancelacion = request.POST.get('motivo_cancelacion', 'Cancelado por administrador')
        solicitud.cancelled_by = request.user
        solicitud.cancelled_at = timezone.now()

        # Si la solicitud estaba aprobada, devolver los días al usuario
        if estado_original == 'APROBADO':
            solicitud.usuario.dias_disponibles += solicitud.dias_solicitados
            solicitud.usuario.save()

        solicitud.save()

        messages.success(
            request,
            f'Solicitud de {solicitud.usuario.get_full_name} cancelada. '
            f'{"Días devueltos al usuario." if estado_original == "APROBADO" else ""}'
        )

        return redirect('admin_management')

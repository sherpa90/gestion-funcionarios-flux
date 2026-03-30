from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, ListView, View, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from .models import SolicitudPermiso
from .forms import SolicitudForm, SolicitudBypassForm, SolicitudAdminForm
from users.models import CustomUser
from core.services import BusinessDayCalculator
from admin_dashboard.utils import registrar_log, get_client_ip
from django.db import transaction

class SolicitudCancelView(LoginRequiredMixin, View):
    """Vista para que el usuario pueda cancelar su propia solicitud pendiente"""
    
    def post(self, request, pk):
        solicitud = get_object_or_404(SolicitudPermiso, pk=pk, usuario=request.user)
        
        # Solo puede cancelar si está pendiente
        if solicitud.estado != 'PENDIENTE':
            messages.error(request, 'Solo puedes cancelar solicitudes pendientes.')
            return redirect('dashboard_funcionario')
        
        # Cancelar la solicitud
        solicitud.estado = 'CANCELADO'
        solicitud.motivo_cancelacion = request.POST.get('motivo_cancelacion', 'Cancelado por el solicitante')
        solicitud.cancelled_by = request.user
        solicitud.cancelled_at = timezone.now()
        solicitud.save()
        
        messages.success(request, 'Solicitud cancelada correctamente.')
        return redirect('dashboard_funcionario')

class SolicitudCreateView(LoginRequiredMixin, CreateView):
    model = SolicitudPermiso
    form_class = SolicitudForm
    template_name = 'permisos/solicitud_form.html'
    success_url = reverse_lazy('dashboard_funcionario')
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        # Calcular fecha termino
        form.instance.fecha_termino = BusinessDayCalculator.calculate_end_date(
            form.instance.fecha_inicio,
            form.instance.dias_solicitados,
            user=self.request.user
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

        # Todas las solicitudes quedan pendientes para llevar un mejor orden (incluyendo las del Director)
        form.instance.estado = 'PENDIENTE'
        registrar_log(
            usuario=self.request.user,
            tipo='CREATE',
            accion='Solicitud de Permiso',
            descripcion=f'Usuario {self.request.user.get_full_name()} solicitó {form.instance.dias_solicitados} días de permiso.',
            ip_address=get_client_ip(self.request)
        )
        messages.success(self.request, 'Solicitud enviada para aprobación.')

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
        try:
            # Calcular fecha termino
            form.instance.fecha_termino = BusinessDayCalculator.calculate_end_date(
                form.instance.fecha_inicio, 
                form.instance.dias_solicitados,
                user=form.instance.usuario
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
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise e

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
        return SolicitudPermiso.objects.filter(usuario=self.request.user).order_by('-fecha_inicio', '-created_at')[:20]
    
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
        # Historial con paginación - mostrar 10 por página (usar h_page)
        historial_qs = SolicitudPermiso.objects.exclude(estado='PENDIENTE').order_by('-updated_at')
        paginator = Paginator(historial_qs, 10)
        page_number = self.request.GET.get('h_page')
        context['historial_page'] = paginator.get_page(page_number)
        # --- Lógica de Resumen Semanal de Aceptados ---
        hoy = timezone.now().date()
        lunes = hoy - timedelta(days=hoy.weekday())

        dias_semana = []
        for i in range(5): # Lunes a Viernes
            fecha_dia = lunes + timedelta(days=i)
            # Contar permisos aprobados que cubren este día, diferenciando Docentes y Asistentes
            solicitudes_dia = SolicitudPermiso.objects.filter(
                estado='APROBADO',
                fecha_inicio__lte=fecha_dia,
                fecha_termino__gte=fecha_dia
            ).select_related('usuario')

            docente_count = 0
            asistente_count = 0
            for solicitud in solicitudes_dia:
                if solicitud.usuario.categoria_funcionario == 'DOCENTE':
                    docente_count += 1
                elif solicitud.usuario.categoria_funcionario == 'ASISTENTE':
                    asistente_count += 1

            dias_semana.append({
                'nombre': ['Lun', 'Mar', 'Mié', 'Jue', 'Vie'][i],
                'count': docente_count + asistente_count,
                'docente_count': docente_count,
                'asistente_count': asistente_count,
                'es_hoy': fecha_dia == hoy
            })
        context['resumen_semanal'] = dias_semana
        
        context['dias_disponibles'] = self.request.user.dias_disponibles
        context['dias_totales'] = getattr(self.request.user, 'dias_totales', 6.0)
        return context

class SolicitudAdminListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = SolicitudPermiso
    template_name = 'permisos/dashboard_director.html'
    context_object_name = 'solicitudes'
    paginate_by = 15

    def test_func(self):
        # DIRECTOR, DIRECTIVO y SECRETARIA pueden acceder
        return self.request.user.role in ['DIRECTOR', 'DIRECTIVO', 'SECRETARIA']

    def get_queryset(self):
        return SolicitudPermiso.objects.filter(estado='PENDIENTE').order_by('created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Historial con paginación - mostrar 10 por página (usar h_page)
        historial_qs = SolicitudPermiso.objects.exclude(estado='PENDIENTE').order_by('-updated_at')
        paginator = Paginator(historial_qs, 10)
        page_number = self.request.GET.get('h_page')
        context['historial_page'] = paginator.get_page(page_number)

        # --- Lógica de Resumen Semanal de Aceptados ---
        hoy = timezone.now().date()
        lunes = hoy - timedelta(days=hoy.weekday())
        
        dias_semana = []
        for i in range(5):
            fecha_dia = lunes + timedelta(days=i)
            count = SolicitudPermiso.objects.filter(
                estado='APROBADO',
                fecha_inicio__lte=fecha_dia,
                fecha_termino__gte=fecha_dia
            ).count()
            dias_semana.append({
                'nombre': ['Lun', 'Mar', 'Mié', 'Jue', 'Vie'][i],
                'count': count,
                'es_hoy': fecha_dia == hoy
            })
        context['resumen_semanal'] = dias_semana
        context['current_filter'] = self.request.GET.get('status', 'all')
        
        return context

class SolicitudActionView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        # Solo DIRECTOR y ADMIN pueden aprobar/rechazar
        return self.request.user.role in ['DIRECTOR', 'ADMIN']

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
                registrar_log(
                    usuario=request.user,
                    tipo='APPROVE',
                    accion='Aprobación de Permiso',
                    descripcion=f'Se aprobó permiso de {solicitud.usuario.get_full_name()} ({solicitud.dias_solicitados} días)',
                    ip_address=get_client_ip(request)
                )
                messages.success(request, 'Solicitud aprobada.')
            else:
                messages.error(request, 'El usuario no tiene saldo suficiente.')
        elif action == 'reject':
            solicitud.estado = 'RECHAZADO'
            solicitud.motivo_rechazo = request.POST.get('motivo_rechazo', '')
            solicitud.save()
            registrar_log(
                usuario=request.user,
                tipo='REJECT',
                accion='Rechazo de Permiso',
                descripcion=f'Se rechazó permiso de {solicitud.usuario.get_full_name()}',
                ip_address=get_client_ip(request)
            )
            messages.success(request, 'Solicitud rechazada.')
        elif action == 'cancel':
            # Solo admins, secretarias y directores pueden cancelar solicitudes aprobadas
            if request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR'] and solicitud.estado == 'APROBADO':
                solicitud.estado = 'CANCELADO'
                solicitud.motivo_cancelacion = request.POST.get('motivo_cancelacion', 'Cancelado por administrador')
                solicitud.cancelled_by = request.user
                solicitud.cancelled_at = timezone.now()
                # Devolver los días al usuario
                solicitud.usuario.dias_disponibles += solicitud.dias_solicitados
                solicitud.usuario.save()
                solicitud.save()
                registrar_log(
                    usuario=request.user,
                    tipo='DELETE',
                    accion='Cancelación Admin de Permiso',
                    descripcion=f'Admin canceló permiso aprobado de {solicitud.usuario.get_full_name()}',
                    ip_address=get_client_ip(request)
                )
                messages.success(request, f'Solicitud cancelada. Se devolvieron {solicitud.dias_solicitados} días a {solicitud.usuario.get_full_name()}.')
            else:
                messages.error(request, 'No tienes permisos para cancelar esta solicitud.')

        return redirect('dashboard_director')


class SolicitudAdminManagementView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Vista administrativa completa para gestionar todas las solicitudes de permisos"""
    model = SolicitudPermiso
    template_name = 'permisos/admin_management.html'
    context_object_name = 'solicitudes'
    paginate_by = 15

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

    def get_queryset(self):
        queryset = SolicitudPermiso.objects.select_related('usuario', 'created_by', 'cancelled_by')

        # Orden por defecto: creación descendente (más recientes primero)
        sort = self.request.GET.get('sort', '-created_at')
        allowed_sorts = ['-created_at', 'created_at', '-fecha_inicio', 'fecha_inicio']
        if sort in allowed_sorts:
            queryset = queryset.order_by(sort)
        else:
            queryset = queryset.order_by('-created_at')

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

        # Estadísticas - UNA sola query con agregación
        from django.db.models import Count, Q
        stats = SolicitudPermiso.objects.aggregate(
            total=Count('id'),
            pendientes=Count('id', filter=Q(estado='PENDIENTE')),
            aprobadas=Count('id', filter=Q(estado='APROBADO')),
            rechazadas=Count('id', filter=Q(estado='RECHAZADO')),
            canceladas=Count('id', filter=Q(estado='CANCELADO')),
        )

        context['estadisticas'] = {
            'total': stats['total'] or 0,
            'pendientes': stats['pendientes'] or 0,
            'aprobadas': stats['aprobadas'] or 0,
            'rechazadas': stats['rechazadas'] or 0,
            'canceladas': stats['canceladas'] or 0,
        }

        # --- Lógica de Resumen Semanal de Aceptados - UNA query por día con aggregation ---
        from datetime import date as date_type
        hoy = timezone.now().date()
        lunes = hoy - timedelta(days=hoy.weekday())

        dias_semana = []
        for i in range(5): # Lunes a Viernes
            fecha_dia = lunes + timedelta(days=i)
            counts = SolicitudPermiso.objects.filter(
                estado='APROBADO',
                fecha_inicio__lte=fecha_dia,
                fecha_termino__gte=fecha_dia
            ).aggregate(
                docente=Count('id', filter=Q(usuario__categoria_funcionario='DOCENTE')),
                asistente=Count('id', filter=Q(usuario__categoria_funcionario='ASISTENTE')),
            )
            docente_count = counts['docente'] or 0
            asistente_count = counts['asistente'] or 0

            dias_semana.append({
                'nombre': ['Lun', 'Mar', 'Mié', 'Jue', 'Vie'][i],
                'count': docente_count + asistente_count,
                'docente_count': docente_count,
                'asistente_count': asistente_count,
                'es_hoy': fecha_dia == hoy
            })
        context['resumen_semanal'] = dias_semana

        # Filtros aplicados
        context['filtros_aplicados'] = {
            'usuario': self.request.GET.get('usuario'),
            'estado': self.request.GET.get('estado'),
            'fecha_desde': self.request.GET.get('fecha_desde'),
            'fecha_hasta': self.request.GET.get('fecha_hasta'),
            'search': self.request.GET.get('search'),
            'sort': self.request.GET.get('sort', '-created_at'),
        }

        return context


class SolicitudAdminEditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Vista para que admins/secretarias editen cualquier solicitud de permiso"""
    model = SolicitudPermiso
    form_class = SolicitudAdminForm
    template_name = 'permisos/admin_edit.html'
    success_url = reverse_lazy('admin_management')

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # No limitar el queryset de usuarios - permitir editar cualquier usuario
        return kwargs

    def form_valid(self, form):
        # 1. Obtener datos originales antes del cambio
        solicitud_actual = self.get_object()
        estado_anterior = solicitud_actual.estado
        dias_anteriores = solicitud_actual.dias_solicitados
        
        # 2. Preparar el objeto para guardar pero sin persistir aún
        solicitud = form.save(commit=False)
        
        # 3. Forzar captura del nuevo estado (desde cleaned_data o POST)
        nuevo_estado = form.cleaned_data.get('estado') or self.request.POST.get('estado')
        
        if not nuevo_estado:
            form.add_error('estado', 'El estado es obligatorio.')
            return self.form_invalid(form)

        # 4. Recalcular fecha término si cambiaron fechas o días
        if 'fecha_inicio' in form.changed_data or 'dias_solicitados' in form.changed_data:
            solicitud.fecha_termino = BusinessDayCalculator.calculate_end_date(
                solicitud.fecha_inicio,
                solicitud.dias_solicitados,
                user=solicitud.usuario
            )

        try:
            with transaction.atomic():
                # 5. Bloquear al usuario para actualización de saldo segura
                usuario = CustomUser.objects.select_for_update().get(pk=solicitud.usuario.pk)
                
                # Caso A: Se desaprueba algo que estaba APROBADO (Devolver días con tope 6.0)
                if estado_anterior == 'APROBADO' and nuevo_estado != 'APROBADO':
                    usuario.dias_disponibles = min(6.0, usuario.dias_disponibles + dias_anteriores)
                    usuario.save()
                
                # Caso B: Se aprueba algo que NO estaba aprobado (Descontar días)
                elif estado_anterior != 'APROBADO' and nuevo_estado == 'APROBADO':
                    if usuario.dias_disponibles >= solicitud.dias_solicitados:
                        usuario.dias_disponibles -= solicitud.dias_solicitados
                        usuario.save()
                    else:
                        form.add_error(None, f"El usuario {usuario.get_full_name()} no tiene días suficientes ({usuario.dias_disponibles} disponibles).")
                        return self.form_invalid(form)
                
                # Caso C: Sigue aprobado pero cambiaron los días solicitados
                elif estado_anterior == 'APROBADO' and nuevo_estado == 'APROBADO' and 'dias_solicitados' in form.changed_data:
                    # Devolvemos lo anterior y descontamos lo nuevo
                    temp_disponibles = min(6.0, usuario.dias_disponibles + dias_anteriores)
                    if temp_disponibles >= solicitud.dias_solicitados:
                        usuario.dias_disponibles = temp_disponibles - solicitud.dias_solicitados
                        usuario.save()
                    else:
                        form.add_error(None, f"Saldo insuficiente para actualizar los días ({temp_disponibles} disponibles tras ajuste).")
                        return self.form_invalid(form)

                # 6. Asignar estado final y otros metadatos
                solicitud.estado = nuevo_estado
                solicitud.updated_at = timezone.now()
                
                # 7. Guardar solicitud (Esto dispara el UPDATE en DB)
                solicitud.save()
                
                # 8. Registrar Auditoría
                registrar_log(
                    usuario=self.request.user,
                    tipo='UPDATE',
                    accion='Edición Admin de Permiso',
                    descripcion=f'Se editó permiso de {solicitud.usuario.get_full_name()} (Estado anterior: {estado_anterior} -> {nuevo_estado})',
                    ip_address=get_client_ip(self.request)
                )
                
                messages.success(self.request, f'Solicitud de {solicitud.usuario.get_full_name()} actualizada exitosamente.')
                return redirect(self.success_url)

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception(f"Error al guardar solicitud: {e}")
            form.add_error(None, "Ocurrió un error inesperado. Intente nuevamente o contacte al administrador.")
            return self.form_invalid(form)


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
            f'Solicitud de {solicitud.usuario.get_full_name()} cancelada. '
            f'{"Días devueltos al usuario." if estado_original == "APROBADO" else ""}'
        )

        return redirect('admin_management')

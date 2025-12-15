from django.shortcuts import render
from django.views.generic import CreateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django import forms
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth, TruncYear
from datetime import datetime
from .models import LicenciaMedica
from .forms import LicenciaForm

class LicenciaCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = LicenciaMedica
    form_class = LicenciaForm
    template_name = 'licencias/licencia_form.html'
    success_url = reverse_lazy('licencia_list')

    def test_func(self):
        # Solo Secretaria y Admin pueden crear licencias
        return self.request.user.role in ['SECRETARIA', 'ADMIN']

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Si no es Secretaria, ocultar el campo usuario
        if self.request.user.role not in ['SECRETARIA', 'ADMIN']:
            form.fields['usuario'].widget = forms.HiddenInput()
            form.fields['usuario'].required = False
        return form

    def form_valid(self, form):
        # Si es Secretaria y seleccionó un usuario, usar ese
        if self.request.user.role in ['SECRETARIA', 'ADMIN'] and form.cleaned_data.get('usuario'):
            form.instance.usuario = form.cleaned_data['usuario']
        else:
            # Si no, usar el usuario actual
            form.instance.usuario = self.request.user
        
        form.instance.created_by = self.request.user
        return super().form_valid(form)

class LicenciaListView(LoginRequiredMixin, ListView):
    model = LicenciaMedica
    template_name = 'licencias/licencia_list.html'
    context_object_name = 'licencias'

    def get_queryset(self):
        queryset = LicenciaMedica.objects.filter(usuario=self.request.user)
        
        # Filtros opcionales
        year = self.request.GET.get('year')
        month = self.request.GET.get('month')
        
        if year:
            queryset = queryset.filter(fecha_inicio__year=year)
        if month:
            queryset = queryset.filter(fecha_inicio__month=month)
        
        return queryset.order_by('-fecha_inicio')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener año y mes seleccionados
        selected_year = self.request.GET.get('year')
        selected_month = self.request.GET.get('month')
        
        context['selected_year'] = int(selected_year) if selected_year else None
        context['selected_month'] = int(selected_month) if selected_month else None
        
        # Años disponibles
        years = LicenciaMedica.objects.filter(
            usuario=self.request.user
        ).dates('fecha_inicio', 'year', order='DESC')
        context['available_years'] = [d.year for d in years]
        
        # Estadísticas por año
        licencias_por_año = LicenciaMedica.objects.filter(
            usuario=self.request.user
        ).annotate(
            year=TruncYear('fecha_inicio')
        ).values('year').annotate(
            total_dias=Sum('dias'),
            total_licencias=Count('id')
        ).order_by('-year')
        
        context['stats_por_año'] = licencias_por_año
        
        # Estadísticas del año seleccionado (o año actual)
        current_year = selected_year if selected_year else datetime.now().year
        licencias_año_actual = LicenciaMedica.objects.filter(
            usuario=self.request.user,
            fecha_inicio__year=current_year
        )
        
        context['total_dias_año'] = licencias_año_actual.aggregate(Sum('dias'))['dias__sum'] or 0
        context['total_licencias_año'] = licencias_año_actual.count()
        
        # Estadísticas por mes del año seleccionado
        licencias_por_mes = licencias_año_actual.annotate(
            month=TruncMonth('fecha_inicio')
        ).values('month').annotate(
            total_dias=Sum('dias'),
            total_licencias=Count('id')
        ).order_by('month')
        
        context['stats_por_mes'] = licencias_por_mes
        context['current_year'] = current_year
        
        return context

from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from permisos.models import SolicitudPermiso
from licencias.models import LicenciaMedica
from users.models import CustomUser
from core.services import BusinessDayCalculator
import openpyxl
from datetime import datetime
from django.utils.timezone import now

class ReportesView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Vista unificada y minimalista de reportes"""
    template_name = 'reportes/reportes.html'

    def test_func(self):
        # Acceso para Director, Secretaria, Admin y Directivos
        return self.request.user.role in ['DIRECTOR', 'SECRETARIA', 'ADMIN', 'DIRECTIVO']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener parámetros de filtro
        search = self.request.GET.get('search', '')
        year = self.request.GET.get('year', '')
        mes = self.request.GET.get('mes', '')
        fecha_inicio = self.request.GET.get('fecha_inicio', '')
        fecha_fin = self.request.GET.get('fecha_fin', '')
        sort_by = self.request.GET.get('sort', 'name')
        
        # Base queryset: incluir todos los funcionarios del sistema
        funcionarios = CustomUser.objects.filter(role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA', 'ADMIN'])
        
        # Filtro de búsqueda por nombre o RUN
        if search:
            funcionarios = funcionarios.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(run__icontains=search)
            )
        
        # Preparar datos de cada funcionario
        empleados_data = []
        for functorio in funcionarios:
            # Obtener permisos aprobados
            permisos = SolicitudPermiso.objects.filter(
                usuario=functorio,
                estado='APROBADO'
            )
            
            # Aplicar filtros de fecha/año
            if year:
                permisos = permisos.filter(fecha_inicio__year=year)
            if mes:
                permisos = permisos.filter(fecha_inicio__month=mes)
            if fecha_inicio:
                permisos = permisos.filter(fecha_inicio__gte=fecha_inicio)
            if fecha_fin:
                permisos = permisos.filter(fecha_inicio__lte=fecha_fin)
            
            dias_usados = permisos.aggregate(Sum('dias_solicitados'))['dias_solicitados__sum'] or 0
            
            # Obtener licencias médicas
            licencias = LicenciaMedica.objects.filter(usuario=functorio)
            
            if year:
                licencias = licencias.filter(fecha_inicio__year=year)
            if mes:
                licencias = licencias.filter(fecha_inicio__month=mes)
            if fecha_inicio:
                licencias = licencias.filter(fecha_inicio__gte=fecha_inicio)
            if fecha_fin:
                licencias = licencias.filter(fecha_inicio__lte=fecha_fin)
            
            total_licencias = licencias.count()
            dias_licencias = licencias.aggregate(Sum('dias'))['dias__sum'] or 0
            
            empleados_data.append({
                'funcionario': functorio,
                'dias_disponibles': functorio.dias_disponibles,
                'dias_usados': dias_usados,
                'total_licencias': total_licencias,
                'dias_licencias': dias_licencias,
            })
        
        # Aplicar ordenamiento
        if sort_by == 'name':
            empleados_data.sort(key=lambda x: (x['funcionario'].last_name, x['funcionario'].first_name))
        elif sort_by == 'name_desc':
            empleados_data.sort(key=lambda x: (x['funcionario'].last_name, x['funcionario'].first_name), reverse=True)
        elif sort_by == 'dias':
            empleados_data.sort(key=lambda x: x['dias_disponibles'], reverse=True)
        elif sort_by == 'dias_asc':
            empleados_data.sort(key=lambda x: x['dias_disponibles'])
        elif sort_by == 'dias_usados':
            empleados_data.sort(key=lambda x: x['dias_usados'], reverse=True)
        elif sort_by == 'dias_usados_asc':
            empleados_data.sort(key=lambda x: x['dias_usados'])
        elif sort_by == 'licencias':
            empleados_data.sort(key=lambda x: x['total_licencias'], reverse=True)
        elif sort_by == 'licencias_asc':
            empleados_data.sort(key=lambda x: x['total_licencias'])
        elif sort_by == 'dias_licencias':
            empleados_data.sort(key=lambda x: x['dias_licencias'], reverse=True)
        elif sort_by == 'dias_licencias_asc':
            empleados_data.sort(key=lambda x: x['dias_licencias'])
        
        context['empleados_data'] = empleados_data
        context['filtros'] = {
            'search': search,
            'year': year,
            'mes': mes,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
        }
        
        # Años disponibles para filtro
        from datetime import datetime
        permisos_years = set(SolicitudPermiso.objects.dates('fecha_inicio', 'year').values_list('fecha_inicio', flat=True))
        licencias_years = set(LicenciaMedica.objects.dates('fecha_inicio', 'year').values_list('fecha_inicio', flat=True))
        all_years = sorted(set([d.year for d in permisos_years] + [d.year for d in licencias_years]), reverse=True)
        context['years'] = all_years if all_years else [datetime.now().year]
        context['current_sort'] = sort_by
        
        return context


class PDFIndividualView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Generar Pdf de un solo empleado"""
    
    def test_func(self):
        return self.request.user.role in ['DIRECTOR', 'SECRETARIA', 'ADMIN', 'DIRECTIVO']

    def get(self, request, usuario_id):
        try:
            functorio = CustomUser.objects.get(pk=usuario_id)
        except CustomUser.DoesNotExist:
            return HttpResponse("Funcionario no encontrado", status=404)
        
        # Obtener parámetros de filtro
        year = request.GET.get('year', '')
        mes = request.GET.get('mes', '')
        fecha_inicio = request.GET.get('fecha_inicio', '')
        fecha_fin = request.GET.get('fecha_fin', '')
        
        # Obtener permisos
        permisos = SolicitudPermiso.objects.filter(
            usuario=functorio,
            estado='APROBADO'
        ).order_by('-fecha_inicio')
        
        if year:
            permisos = permisos.filter(fecha_inicio__year=year)
        if mes:
            permisos = permisos.filter(fecha_inicio__month=mes)
        if fecha_inicio:
            permisos = permisos.filter(fecha_inicio__gte=fecha_inicio)
        if fecha_fin:
            permisos = permisos.filter(fecha_inicio__lte=fecha_fin)
        
        dias_usados = permisos.aggregate(Sum('dias_solicitados'))['dias_solicitados__sum'] or 0
        
        # Obtener licencias
        licencias = LicenciaMedica.objects.filter(usuario=functorio).order_by('-fecha_inicio')
        
        if year:
            licencias = licencias.filter(fecha_inicio__year=year)
        if mes:
            licencias = licencias.filter(fecha_inicio__month=mes)
        if fecha_inicio:
            licencias = licencias.filter(fecha_inicio__gte=fecha_inicio)
        if fecha_fin:
            licencias = licencias.filter(fecha_inicio__lte=fecha_fin)
        
        html_string = render_to_string('reportes/pdf_individual.html', {
            'functorio': functorio,
            'permisos': permisos,
            'licencias': licencias,
            'dias_usados': dias_usados,
            'total_dias_licencias': licencias.aggregate(Sum('dias'))['dias__sum'] or 0,
            'year': year,
            'mes': mes,
            'mes_nombre': {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}.get(int(mes) if mes else 0, ''),
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'fecha_exportacion': now().strftime('%d/%m/%Y %H:%M'),
            'director': CustomUser.objects.filter(role='DIRECTOR').first(),
        })

        html = HTML(string=html_string)
        result = html.write_pdf()

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename=reporte_{functorio.run}.pdf'
        response.write(result)
        return response


class PDFColectivoView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Generar Pdf de todos los empleados filtrados"""
    
    def test_func(self):
        return self.request.user.role in ['DIRECTOR', 'SECRETARIA', 'ADMIN', 'DIRECTIVO']

    def get(self, request):
        # Obtener parámetros de filtro
        search = request.GET.get('search', '')
        year = request.GET.get('year', '')
        mes = request.GET.get('mes', '')
        fecha_inicio = request.GET.get('fecha_inicio', '')
        fecha_fin = request.GET.get('fecha_fin', '')
        
        # Filtrar funcionarios - EXCLUIR ADMIN
        funcionarios = CustomUser.objects.filter(role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA'])
        if search:
            funcionarios = funcionarios.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(run__icontains=search)
            )
        
        # Preparar datos
        empleados_data = []
        total_dias_disponibles = 0
        total_licencias = 0
        
        for functorio in funcionarios.order_by('last_name', 'first_name'):
            permisos = SolicitudPermiso.objects.filter(usuario=functorio, estado='APROBADO')
            if year:
                permisos = permisos.filter(fecha_inicio__year=year)
            if mes:
                permisos = permisos.filter(fecha_inicio__month=mes)
            if fecha_inicio:
                permisos = permisos.filter(fecha_inicio__gte=fecha_inicio)
            if fecha_fin:
                permisos = permisos.filter(fecha_inicio__lte=fecha_fin)
            
            licencias = LicenciaMedica.objects.filter(usuario=functorio)
            if year:
                licencias = licencias.filter(fecha_inicio__year=year)
            if mes:
                licencias = licencias.filter(fecha_inicio__month=mes)
            if fecha_inicio:
                licencias = licencias.filter(fecha_inicio__gte=fecha_inicio)
            if fecha_fin:
                licencias = licencias.filter(fecha_inicio__lte=fecha_fin)
            
            dias_usados = permisos.aggregate(Sum('dias_solicitados'))['dias_solicitados__sum'] or 0
            dias_lic = licencias.aggregate(Sum('dias'))['dias__sum'] or 0
            total_lic = licencias.count()
            
            total_dias_disponibles += float(functorio.dias_disponibles)
            total_licencias += total_lic
            
            empleados_data.append({
                'funcionario': functorio,
                'dias_disponibles': functorio.dias_disponibles,
                'dias_usados': dias_usados,
                'total_licencias': total_lic,
                'dias_licencias': dias_lic,
            })
        
        html_string = render_to_string('reportes/pdf_colectivo.html', {
            'empleados_data': empleados_data,
            'year': year,
            'mes': mes,
            'mes_nombre': {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}.get(mes, ''),
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'total_funcionarios': len(empleados_data),
            'total_dias_disponibles': total_dias_disponibles,
            'total_licencias': total_licencias,
            'fecha_exportacion': now().strftime('%d/%m/%Y %H:%M'),
            'director': CustomUser.objects.filter(role='DIRECTOR').first(),
        })

        html = HTML(string=html_string)
        result = html.write_pdf()

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename=reporte_colectivo.pdf'
        response.write(result)
        return response


class ExportarExcelView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Exportar reporte detallado a Excel"""
    
    def test_func(self):
        return self.request.user.role in ['DIRECTOR', 'SECRETARIA', 'ADMIN', 'DIRECTIVO']

    def get(self, request):
        # Obtener parámetros de filtro
        search = request.GET.get('search', '')
        year = request.GET.get('year', '')
        mes = request.GET.get('mes', '')
        fecha_inicio = request.GET.get('fecha_inicio', '')
        fecha_fin = request.GET.get('fecha_fin', '')
        
        # Filtrar funcionarios
        funcionarios = CustomUser.objects.filter(role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA', 'ADMIN'])
        if search:
            funcionarios = funcionarios.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(run__icontains=search)
            )
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Reporte Detallado"
        
        # Encabezados
        ws.append(['Nombre', 'RUN', 'Rol', 'Días Disponibles', 'Días Usados', 'Días Licencia', 'Total Licencias'])
        
        # Preparar datos
        for functorio in funcionarios.order_by('last_name', 'first_name'):
            permisos = SolicitudPermiso.objects.filter(usuario=functorio, estado='APROBADO')
            if year:
                permisos = permisos.filter(fecha_inicio__year=year)
            if mes:
                permisos = permisos.filter(fecha_inicio__month=mes)
            if fecha_inicio:
                permisos = permisos.filter(fecha_inicio__gte=fecha_inicio)
            if fecha_fin:
                permisos = permisos.filter(fecha_inicio__lte=fecha_fin)
            
            licencias = LicenciaMedica.objects.filter(usuario=functorio)
            if year:
                licencias = licencias.filter(fecha_inicio__year=year)
            if mes:
                licencias = licencias.filter(fecha_inicio__month=mes)
            if fecha_inicio:
                licencias = licencias.filter(fecha_inicio__gte=fecha_inicio)
            if fecha_fin:
                licencias = licencias.filter(fecha_inicio__lte=fecha_fin)
            
            dias_usados = permisos.aggregate(Sum('dias_solicitados'))['dias_solicitados__sum'] or 0
            dias_licencia = licencias.aggregate(Sum('dias'))['dias__sum'] or 0
            
            ws.append([
                functorio.get_full_name(),
                functorio.run,
                functorio.get_role_display(),
                functorio.dias_disponibles,
                dias_usados,
                dias_licencia,
                licencias.count()
            ])
        
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=reporte_detallado.xlsx'
        wb.save(response)
        return response

class ReporteMensualDiasAdministrativosView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Generar Pdf mensual de resumen de días administrativos"""
    
    def test_func(self):
        return self.request.user.role in ['DIRECTOR', 'SECRETARIA', 'ADMIN', 'DIRECTIVO']

    def get(self, request):
        # Obtener parámetros
        year = request.GET.get('year', str(datetime.now().year))
        mes = request.GET.get('mes', str(datetime.now().month))
        
        try:
            year = int(year)
            mes = int(mes)
        except ValueError:
            year = datetime.now().year
            mes = datetime.now().month
        
        # Obtener todos los permisos aprobados del mes
        permisos = SolicitudPermiso.objects.filter(
            estado='APROBADO',
            fecha_inicio__year=year,
            fecha_inicio__month=mes
        ).select_related('usuario').order_by('created_at', 'fecha_inicio')
        
        # Preparar datos para el reporte - cada permiso es una fila
        empleados_data = []
        
        for permiso in permisos:
            empleados_data.append({
                'funcionario': permiso.usuario,
                'run': permiso.usuario.run,
                'nombre_completo': permiso.usuario.get_full_name() or permiso.usuario.username,
                'dias_solicitados': permiso.dias_solicitados,
                'dias_disponibles': permiso.usuario.dias_disponibles if permiso.usuario.dias_disponibles else 0,
                'fecha_desde': permiso.fecha_inicio,
                'fecha_hasta': permiso.fecha_termino,
                'fecha_solicitud': permiso.created_at,
            })
        
        # Generar Pdf
        html_string = render_to_string('reportes/reporte_mensual_dias_administrativos.html', {
            'empleados_data': empleados_data,
            'year': year,
            'mes': mes,
            'mes_nombre': {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}.get(mes, ''),
            'total_funcionarios': len(empleados_data),
            'total_dias': sum(e['dias_solicitados'] for e in empleados_data),
            'fecha_exportacion': now().strftime('%d/%m/%Y %H:%M'),
            'director': CustomUser.objects.filter(role='DIRECTOR').first(),
            'establecimiento': 'Dirección de Educación Municipal Los Lagos',
        })

        html = HTML(string=html_string)
        result = html.write_pdf()

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename=reporte_dias_administrativos_{year}_{mes:02d}.pdf'
        response.write(result)
        return response

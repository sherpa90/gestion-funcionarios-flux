from django.views.generic import TemplateView, View
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from permisos.models import SolicitudPermiso
from licencias.models import LicenciaMedica
from asistencia.models import RegistroAsistencia, HorarioFuncionario, DiaHorario
from users.models import CustomUser
from core.services import BusinessDayCalculator
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import datetime, time
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

            # Obtener registros de asistencia para contar atrasos e inasistencias
            registros_asistencia = RegistroAsistencia.objects.filter(funcionario=functorio)
            if year:
                registros_asistencia = registros_asistencia.filter(fecha__year=year)
            if mes:
                registros_asistencia = registros_asistencia.filter(fecha__month=mes)
            if fecha_inicio:
                registros_asistencia = registros_asistencia.filter(fecha__gte=fecha_inicio)
            if fecha_fin:
                registros_asistencia = registros_asistencia.filter(fecha__lte=fecha_fin)

            total_atrasos = registros_asistencia.filter(estado='RETRASO').count()
            total_inasistencias = registros_asistencia.filter(estado='AUSENTE').count()
            total_minutos_retraso = registros_asistencia.filter(estado='RETRASO').aggregate(
                total=Sum('minutos_retraso'))['total'] or 0
            
            empleados_data.append({
                'funcionario': functorio,
                'cargo': functorio.get_funcion_display() or functorio.get_tipo_funcionario_display() or functorio.get_role_display(),
                'dias_disponibles': functorio.dias_disponibles,
                'dias_usados': dias_usados,
                'total_licencias': total_licencias,
                'dias_licencias': dias_licencias,
                'permisos': permisos.order_by('fecha_inicio'),
                'licencias': licencias.order_by('fecha_inicio'),
                'total_atrasos': total_atrasos,
                'total_inasistencias': total_inasistencias,
                'total_minutos_retraso': total_minutos_retraso,
            })
        
        # Aplicar ordenamiento
        if sort_by == 'name':
            empleados_data.sort(key=lambda x: (x['funcionario'].first_name, x['funcionario'].last_name))
        elif sort_by == 'name_desc':
            empleados_data.sort(key=lambda x: (x['funcionario'].first_name, x['funcionario'].last_name), reverse=True)
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
        elif sort_by == 'inasistencias':
            empleados_data.sort(key=lambda x: x['total_inasistencias'], reverse=True)
        elif sort_by == 'inasistencias_asc':
            empleados_data.sort(key=lambda x: x['total_inasistencias'])
        elif sort_by == 'atrasos':
            empleados_data.sort(key=lambda x: x['total_atrasos'], reverse=True)
        elif sort_by == 'atrasos_asc':
            empleados_data.sort(key=lambda x: x['total_atrasos'])
        
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

        # Obtener registros de asistencia para contar atrasos e inasistencias
        registros_asistencia = RegistroAsistencia.objects.filter(funcionario=functorio)
        if year:
            registros_asistencia = registros_asistencia.filter(fecha__year=year)
        if mes:
            registros_asistencia = registros_asistencia.filter(fecha__month=mes)
        if fecha_inicio:
            registros_asistencia = registros_asistencia.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            registros_asistencia = registros_asistencia.filter(fecha__lte=fecha_fin)

        total_inasistencias = registros_asistencia.filter(estado='AUSENTE').count()
        total_atrasos = registros_asistencia.filter(estado='RETRASO').count()
        total_minutos_retraso = registros_asistencia.filter(estado='RETRASO').aggregate(
            total=Sum('minutos_retraso'))['total'] or 0
        
        html_string = render_to_string('reportes/pdf_individual.html', {
            'functorio': functorio,
            'cargo': functorio.get_funcion_display() or functorio.get_tipo_funcionario_display() or functorio.get_role_display(),
            'permisos': permisos,
            'licencias': licencias,
            'dias_usados': dias_usados,
            'total_dias_licencias': licencias.aggregate(Sum('dias'))['dias__sum'] or 0,
            'total_inasistencias': total_inasistencias,
            'total_atrasos': total_atrasos,
            'total_minutos_retraso': total_minutos_retraso,
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



class MiReportePDFView(LoginRequiredMixin, View):
    """Genera el PDF individual del usuario actualmente autenticado."""

    def get(self, request):
        functorio = request.user

        year = request.GET.get('year', '')
        mes  = request.GET.get('mes', '')
        fecha_inicio = request.GET.get('fecha_inicio', '')
        fecha_fin    = request.GET.get('fecha_fin', '')

        permisos = SolicitudPermiso.objects.filter(
            usuario=functorio,
            estado='APROBADO'
        ).order_by('-fecha_inicio')
        if year:        permisos = permisos.filter(fecha_inicio__year=year)
        if mes:         permisos = permisos.filter(fecha_inicio__month=mes)
        if fecha_inicio:permisos = permisos.filter(fecha_inicio__gte=fecha_inicio)
        if fecha_fin:   permisos = permisos.filter(fecha_inicio__lte=fecha_fin)

        dias_usados = permisos.aggregate(Sum('dias_solicitados'))['dias_solicitados__sum'] or 0

        licencias = LicenciaMedica.objects.filter(usuario=functorio).order_by('-fecha_inicio')
        if year:        licencias = licencias.filter(fecha_inicio__year=year)
        if mes:         licencias = licencias.filter(fecha_inicio__month=mes)
        if fecha_inicio:licencias = licencias.filter(fecha_inicio__gte=fecha_inicio)
        if fecha_fin:   licencias = licencias.filter(fecha_inicio__lte=fecha_fin)

        registros_asistencia = RegistroAsistencia.objects.filter(funcionario=functorio)
        if year:        registros_asistencia = registros_asistencia.filter(fecha__year=year)
        if mes:         registros_asistencia = registros_asistencia.filter(fecha__month=mes)
        if fecha_inicio:registros_asistencia = registros_asistencia.filter(fecha__gte=fecha_inicio)
        if fecha_fin:   registros_asistencia = registros_asistencia.filter(fecha__lte=fecha_fin)

        total_inasistencias = registros_asistencia.filter(estado='AUSENTE').count()
        total_atrasos       = registros_asistencia.filter(estado='RETRASO').count()
        total_minutos_retraso = registros_asistencia.filter(estado='RETRASO').aggregate(
            total=Sum('minutos_retraso'))['total'] or 0

        html_string = render_to_string('reportes/pdf_individual.html', {
            'functorio': functorio,
            'cargo': functorio.get_funcion_display() or functorio.get_tipo_funcionario_display() or functorio.get_role_display(),
            'permisos': permisos,
            'licencias': licencias,
            'dias_usados': dias_usados,
            'total_dias_licencias': licencias.aggregate(Sum('dias'))['dias__sum'] or 0,
            'total_inasistencias': total_inasistencias,
            'total_atrasos': total_atrasos,
            'total_minutos_retraso': total_minutos_retraso,
            'year': year,
            'mes': mes,
            'mes_nombre': {1:'Enero',2:'Febrero',3:'Marzo',4:'Abril',5:'Mayo',6:'Junio',
                           7:'Julio',8:'Agosto',9:'Septiembre',10:'Octubre',11:'Noviembre',12:'Diciembre'}.get(int(mes) if mes else 0, ''),
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'fecha_exportacion': now().strftime('%d/%m/%Y %H:%M'),
            'director': CustomUser.objects.filter(role='DIRECTOR').first(),
        })

        html   = HTML(string=html_string)
        result = html.write_pdf()

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename=mi_reporte_{functorio.run}.pdf'
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
        
        for functorio in funcionarios.order_by('first_name', 'last_name'):
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

            # Obtener registros de asistencia para contar atrasos e inasistencias
            registros_asistencia = RegistroAsistencia.objects.filter(funcionario=functorio)
            if year:
                registros_asistencia = registros_asistencia.filter(fecha__year=year)
            if mes:
                registros_asistencia = registros_asistencia.filter(fecha__month=mes)
            if fecha_inicio:
                registros_asistencia = registros_asistencia.filter(fecha__gte=fecha_inicio)
            if fecha_fin:
                registros_asistencia = registros_asistencia.filter(fecha__lte=fecha_fin)

            total_atrasos = registros_asistencia.filter(estado='RETRASO').count()
            total_inasistencias = registros_asistencia.filter(estado='AUSENTE').count()
            total_minutos_retraso = registros_asistencia.filter(estado='RETRASO').aggregate(
                total=Sum('minutos_retraso'))['total'] or 0

            total_dias_disponibles += float(functorio.dias_disponibles)
            total_licencias += total_lic

            empleados_data.append({
                'funcionario': functorio,
                'dias_disponibles': functorio.dias_disponibles,
                'dias_usados': dias_usados,
                'total_licencias': total_lic,
                'dias_licencias': dias_lic,
                'total_atrasos': total_atrasos,
                'total_inasistencias': total_inasistencias,
                'total_minutos_retraso': total_minutos_retraso,
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
        ws.append(['Nombre', 'RUN', 'Cargo', 'Inasistencias sin Justificar', 'Atrasos', 'Min. Retraso Total', 'Días Disponibles', 'Días Usados', 'Días Licencia', 'Total Licencias'])
        
        # Preparar datos
        for functorio in funcionarios.order_by('first_name', 'last_name'):
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

            # Contar inasistencias y atrasos
            registros = RegistroAsistencia.objects.filter(funcionario=functorio)
            if year:
                registros = registros.filter(fecha__year=year)
            if mes:
                registros = registros.filter(fecha__month=mes)
            if fecha_inicio:
                registros = registros.filter(fecha__gte=fecha_inicio)
            if fecha_fin:
                registros = registros.filter(fecha__lte=fecha_fin)

            total_inasistencias = registros.filter(estado='AUSENTE').count()
            total_atrasos = registros.filter(estado='RETRASO').count()
            total_minutos_retraso = registros.filter(estado='RETRASO').aggregate(
                total=Sum('minutos_retraso'))['total'] or 0
            
            ws.append([
                functorio.get_full_name(),
                functorio.run,
                functorio.get_funcion_display() or functorio.get_tipo_funcionario_display() or functorio.get_role_display(),
                total_inasistencias,
                total_atrasos,
                total_minutos_retraso,
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
        ).select_related('usuario').order_by('fecha_inicio', 'created_at')
        
        # Preparar datos para el reporte - cada permiso es una fila
        empleados_data = []
        
        for permiso in permisos:
            empleados_data.append({
                'funcionario': permiso.usuario,
                'cargo': permiso.usuario.get_funcion_display() or permiso.usuario.get_tipo_funcionario_display() or permiso.usuario.get_role_display(),
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

class ExportarDAEMExcelView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Exportar reporte DAEM a Excel (Multi-pestaña)"""
    
    def test_func(self):
        return self.request.user.role in ['DIRECTOR', 'SECRETARIA', 'ADMIN', 'DIRECTIVO']

    def get(self, request):
        year = request.GET.get('year', '')
        mes = request.GET.get('mes', '')
        
        wb = openpyxl.Workbook()
        
        # Pestaña 1: Nómina
        ws_nomina = wb.active
        ws_nomina.title = "Nómina"
        ws_nomina.append(['N°', 'Funcionario', 'RUN', 'Cargo'])
        for col in ['A']:
            ws_nomina.column_dimensions[col].width = 10
        for col in ['B', 'C', 'D']:
            ws_nomina.column_dimensions[col].width = 30

        funcionarios = CustomUser.objects.filter(role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA', 'ADMIN']).order_by('first_name', 'last_name')
        for i, f in enumerate(funcionarios, 1):
            ws_nomina.append([i, f.get_full_name() or f.username, f.run, f.get_funcion_display() or ""])
            
        # Pestaña 2: Permisos Administrativos
        ws_permisos = wb.create_sheet(title="Permisos Administrativos")
        ws_permisos.append(['N°', 'Funcionario', 'RUN', 'Días Solicitados', 'Fecha Desde', 'Fecha Hasta', 'Fecha Solicitud'])
        for col in ['A']:
            ws_permisos.column_dimensions[col].width = 10
        for col in ['B', 'C', 'D', 'E', 'F', 'G']:
            ws_permisos.column_dimensions[col].width = 25

        permisos = SolicitudPermiso.objects.filter(estado='APROBADO', usuario__in=funcionarios).select_related('usuario').order_by('usuario__first_name', 'usuario__last_name', 'fecha_inicio')
        if year:
            permisos = permisos.filter(fecha_inicio__year=year)
        if mes:
            permisos = permisos.filter(fecha_inicio__month=mes)
            
        for i, p in enumerate(permisos, 1):
            ws_permisos.append([
                i,
                p.usuario.get_full_name() or p.usuario.username,
                p.usuario.run,
                float(p.dias_solicitados),
                p.fecha_inicio.strftime("%d-%m-%Y") if p.fecha_inicio else "",
                p.fecha_termino.strftime("%d-%m-%Y") if p.fecha_termino else "",
                p.created_at.strftime("%d-%m-%Y") if p.created_at else ""
            ])

        # Pestaña 3: Licencias Médicas
        ws_licencias = wb.create_sheet(title="Licencias Médicas")
        ws_licencias.append(['N°', 'Funcionario', 'RUN', 'Tipo de Licencia', 'Días', 'Fecha Desde', 'Fecha Hasta'])
        for col in ['A']:
            ws_licencias.column_dimensions[col].width = 10
        for col in ['B', 'C', 'D', 'E', 'F', 'G']:
            ws_licencias.column_dimensions[col].width = 25

        licencias = LicenciaMedica.objects.filter(usuario__in=funcionarios).select_related('usuario').order_by('usuario__first_name', 'usuario__last_name', 'fecha_inicio')
        if year:
            licencias = licencias.filter(fecha_inicio__year=year)
        if mes:
            licencias = licencias.filter(fecha_inicio__month=mes)
            
        for i, lic in enumerate(licencias, 1):
            ws_licencias.append([
                i,
                lic.usuario.get_full_name() or lic.usuario.username,
                lic.usuario.run,
                "Licencia Médica",
                lic.dias,
                lic.fecha_inicio.strftime("%d-%m-%Y") if lic.fecha_inicio else "",
                lic.fecha_termino.strftime("%d-%m-%Y") if lic.fecha_termino else ""
            ])

        # Pestaña 4: Asistencia (Inasistencias y Atrasos)
        ws_asistencia = wb.create_sheet(title="Asistencia")
        ws_asistencia.append(['N°', 'Funcionario', 'RUN', 'Inasistencias', 'Atrasos', 'Min. Retraso Total'])
        for col in ['A']:
            ws_asistencia.column_dimensions[col].width = 10
        for col in ['B', 'C']:
            ws_asistencia.column_dimensions[col].width = 30
        for col in ['D', 'E', 'F']:
            ws_asistencia.column_dimensions[col].width = 20

        for i, f in enumerate(funcionarios, 1):
            registros = RegistroAsistencia.objects.filter(funcionario=f)
            if year:
                registros = registros.filter(fecha__year=year)
            if mes:
                registros = registros.filter(fecha__month=mes)
            total_inasistencias = registros.filter(estado='AUSENTE').count()
            total_atrasos = registros.filter(estado='RETRASO').count()
            total_minutos_retraso = registros.filter(estado='RETRASO').aggregate(
                total=Sum('minutos_retraso'))['total'] or 0
            ws_asistencia.append([
                i,
                f.get_full_name() or f.username,
                f.run,
                total_inasistencias,
                total_atrasos,
                total_minutos_retraso
            ])

        # Pestañas estilo (Header en negrita)
        from openpyxl.styles import Font, PatternFill
        header_font = Font(bold=True, color="FFFFFF")
        fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")

        for ws in [ws_nomina, ws_permisos, ws_licencias, ws_asistencia]:
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = fill

        # Generar archivo
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        filename = f"reporte_daem"
        if mes and year:
            filename += f"_{mes}_{year}"
        elif year:
            filename += f"_{year}"
        response['Content-Disposition'] = f'attachment; filename={filename}.xlsx'
        wb.save(response)
        return response

class ExportarHorariosExcelView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Exportar los horarios semanales de todos los funcionarios a Excel"""
    
    def test_func(self):
        return self.request.user.role in ['DIRECTOR', 'SECRETARIA', 'ADMIN', 'DIRECTIVO']

    def get(self, request):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Horarios del Personal"
        
        # Estilos
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
        alignment = Alignment(horizontal="center", vertical="center")
        
        # Encabezados
        headers = ['N°', 'Funcionario', 'RUN', 'Cargo', 
                   'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo', 
                   'Horas Semanales']
        ws.append(headers)
        
        # Aplicar estilos a encabezados
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = alignment

        # Ajustar anchos de columna
        ws.column_dimensions['B'].width = 35
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 25
        for col in ['E', 'F', 'G', 'H', 'I', 'J', 'K']:
            ws.column_dimensions[col].width = 18
        ws.column_dimensions['L'].width = 18

        # Obtener todos los funcionarios activos
        funcionarios = CustomUser.objects.filter(
            is_active=True,
            role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA', 'ADMIN']
        ).order_by('first_name', 'last_name')

        for i, f in enumerate(funcionarios, 1):
            horario = getattr(f, 'horario', None)
            dias_dict = {}
            total_minutos = 0
            
            if horario:
                for d in horario.dias.all():
                    if d.activo and d.hora_entrada and d.hora_salida:
                        dias_dict[d.dia_semana] = f"{d.hora_entrada.strftime('%H:%M')} - {d.hora_salida.strftime('%H:%M')}"
                        
                        # Calcular minutos
                        h1, m1 = d.hora_entrada.hour, d.hora_entrada.minute
                        h2, m2 = d.hora_salida.hour, d.hora_salida.minute
                        min1 = h1 * 60 + m1
                        min2 = h2 * 60 + m2
                        if min2 < min1: min2 += 24 * 60 # Turno nocturno
                        total_minutos += (min2 - min1)
                    else:
                        dias_dict[d.dia_semana] = "Libre"
            
            # Formatear total horas
            h_total = total_minutos // 60
            m_total = total_minutos % 60
            horas_str = f"{h_total}h {m_total}m" if m_total > 0 else f"{h_total}h"
            if total_minutos == 0: horas_str = "No configurado"

            row = [
                i,
                f.get_full_name(),
                f.run,
                f.get_funcion_display() or f.get_role_display(),
                dias_dict.get(0, "Libre"), # Lun
                dias_dict.get(1, "Libre"), # Mar
                dias_dict.get(2, "Libre"), # Mié
                dias_dict.get(3, "Libre"), # Jue
                dias_dict.get(4, "Libre"), # Vie
                dias_dict.get(5, "Libre"), # Sáb
                dias_dict.get(6, "Libre"), # Dom
                horas_str
            ]
            ws.append(row)
            
            # Centrar celdas de horarios
            for cell in ws[ws.max_row][4:]:
                cell.alignment = alignment

        # Generar archivo
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=horarios_personal_{datetime.now().strftime("%Y%m%d")}.xlsx'
        wb.save(response)
        return response

class ExportarHorariosPDFView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Exportar los horarios semanales de todos los funcionarios a PDF"""
    
    def test_func(self):
        return self.request.user.role in ['DIRECTOR', 'SECRETARIA', 'ADMIN', 'DIRECTIVO']

    def get(self, request):
        # Obtener todos los funcionarios activos
        funcionarios = CustomUser.objects.filter(
            is_active=True,
            role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA', 'ADMIN']
        ).order_by('first_name', 'last_name')

        empleados_data = []
        DIA_NAMES = {0: 'Lun', 1: 'Mar', 2: 'Mié', 3: 'Jue', 4: 'Vie', 5: 'Sáb', 6: 'Dom'}

        for f in funcionarios:
            horario = getattr(f, 'horario', None)
            dias_list = []
            total_minutos = 0
            
            # Inicializar con "Libre"
            dias_data = {i: "Libre" for i in range(7)}
            
            if horario:
                for d in horario.dias.all():
                    if d.activo and d.hora_entrada and d.hora_salida:
                        dias_data[d.dia_semana] = f"{d.hora_entrada.strftime('%H:%M')} - {d.hora_salida.strftime('%H:%M')}"
                        
                        # Calcular minutos
                        h1, m1 = d.hora_entrada.hour, d.hora_entrada.minute
                        h2, m2 = d.hora_salida.hour, d.hora_salida.minute
                        min1 = h1 * 60 + m1
                        min2 = h2 * 60 + m2
                        if min2 < min1: min2 += 24 * 60
                        total_minutos += (min2 - min1)

            # Formatear total horas
            h_total = total_minutos // 60
            m_total = total_minutos % 60
            horas_str = f"{h_total}h {m_total}m" if m_total > 0 else f"{h_total}h"
            if total_minutos == 0: horas_str = "N/C"

            empleados_data.append({
                'nombre': f.get_full_name(),
                'run': f.run,
                'cargo': f.get_funcion_display() or f.get_role_display(),
                'dias': [dias_data[i] for i in range(7)],
                'total_horas': horas_str
            })

        html_string = render_to_string('reportes/pdf_horarios.html', {
            'empleados_data': empleados_data,
            'fecha_exportacion': now().strftime('%d/%m/%Y %H:%M'),
            'director': CustomUser.objects.filter(role='DIRECTOR').first(),
        })

        html = HTML(string=html_string)
        result = html.write_pdf()

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename=horarios_personal_{datetime.now().strftime("%Y%m%d")}.pdf'
        response.write(result)
        return response

class MiHorarioPDFView(LoginRequiredMixin, View):
    """Genera el PDF del horario semanal del usuario actualmente autenticado."""

    def get(self, request):
        f = request.user
        horario = getattr(f, 'horario', None)
        total_minutos = 0
        
        # Inicializar con "Libre"
        dias_data = {i: "Libre" for i in range(7)}
        
        if horario:
            for d in horario.dias.all():
                if d.activo and d.hora_entrada and d.hora_salida:
                    dias_data[d.dia_semana] = f"{d.hora_entrada.strftime('%H:%M')} - {d.hora_salida.strftime('%H:%M')}"
                    
                    # Calcular minutos
                    h1, m1 = d.hora_entrada.hour, d.hora_entrada.minute
                    h2, m2 = d.hora_salida.hour, d.hora_salida.minute
                    min1 = h1 * 60 + m1
                    min2 = h2 * 60 + m2
                    if min2 < min1: min2 += 24 * 60
                    total_minutos += (min2 - min1)

        # Formatear total horas
        h_total = total_minutos // 60
        m_total = total_minutos % 60
        horas_str = f"{h_total}h {m_total}m" if m_total > 0 else f"{h_total}h"
        if total_minutos == 0: horas_str = "N/C"

        empleado_data = {
            'nombre': f.get_full_name(),
            'run': f.run,
            'cargo': f.get_funcion_display() or f.get_role_display(),
            'dias': [dias_data[i] for i in range(7)],
            'total_horas': horas_str
        }

        html_string = render_to_string('reportes/pdf_horarios.html', {
            'empleados_data': [empleado_data],
            'fecha_exportacion': now().strftime('%d/%m/%Y %H:%M'),
            'director': CustomUser.objects.filter(role='DIRECTOR').first(),
            'es_individual': True
        })

        html = HTML(string=html_string)
        result = html.write_pdf()

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename=mi_horario_{f.run}.pdf'
        response.write(result)
        return response




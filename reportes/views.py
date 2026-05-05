from django.views.generic import TemplateView, View
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from permisos.models import SolicitudPermiso
from licencias.models import LicenciaMedica
from asistencia.models import RegistroAsistencia, HorarioFuncionario, DiaHorario, AlegacionAsistencia
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


class ReporteMensualDiasAdministrativosExcelView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Generar Excel mensual de resumen de días administrativos"""

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

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Días Administrativos {mes:02d}-{year}"

        # Encabezados
        headers = ['N°', 'Nombre Completo', 'RUN', 'Cargo', 'Días Solicitados', 'Días Disponibles', 'Fecha Desde', 'Fecha Hasta', 'Fecha Solicitud']
        ws.append(headers)

        # Column widths
        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 25
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 20
        ws.column_dimensions['E'].width = 15
        ws.column_dimensions['F'].width = 15
        ws.column_dimensions['G'].width = 12
        ws.column_dimensions['H'].width = 12
        ws.column_dimensions['I'].width = 15

        for i, permiso in enumerate(permisos, 1):
            ws.append([
                i,
                permiso.usuario.get_full_name() or permiso.usuario.username,
                permiso.usuario.run,
                permiso.usuario.get_funcion_display() or permiso.usuario.get_tipo_funcionario_display() or permiso.usuario.get_role_display(),
                permiso.dias_solicitados,
                permiso.usuario.dias_disponibles if permiso.usuario.dias_disponibles else 0,
                permiso.fecha_inicio.strftime("%d/%m/%Y") if permiso.fecha_inicio else "",
                permiso.fecha_termino.strftime("%d/%m/%Y") if permiso.fecha_termino else "",
                permiso.created_at.strftime("%d/%m/%Y") if permiso.created_at else ""
            ])

        # Styling
        header_font = Font(bold=True, color="FFFFFF")
        fill = PatternFill(start_color="7C3AED", end_color="7C3AED", fill_type="solid")
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = fill

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        filename = f'reporte_dias_administrativos_{year}_{mes:02d}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        wb.save(response)
        return response


class ExportarDAEMExcelView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Exportar reporte DAEM/DAEM3 a Excel"""

    def test_func(self):
        return self.request.user.role in ['DIRECTOR', 'SECRETARIA', 'ADMIN', 'DIRECTIVO']

    def get(self, request):
        year = request.GET.get('year', '')
        mes = request.GET.get('mes', '')
        tipo = request.GET.get('tipo', '').lower()  # Para DAEM3, convertir a minúsculas

        # Si es DAEM3, mostrar formato de asistencia laboral
        if tipo in ['docentes', 'docente', 'asistentes', 'asistente']:
            return self._exportar_daem3_excel(year, mes, tipo)

        # Formato regular DAEM (permisos administrativos)
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
        ws_permisos.append(['N°', 'Nombre Completo', 'RUN', 'Cargo', 'Tipo de Permiso Administrativo', 'Fecha de Inicio', 'Fecha de Término', 'Cantidad de Días', 'Observaciones'])
        for col in ['A']:
            ws_permisos.column_dimensions[col].width = 10
        for col in ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']:
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
                p.usuario.get_funcion_display() or "",
                "",
                p.fecha_inicio.strftime("%d-%m-%Y") if p.fecha_inicio else "",
                p.fecha_termino.strftime("%d-%m-%Y") if p.fecha_termino else "",
                float(p.dias_solicitados),
                ""
            ])

        # Firma
        firma_row = len(permisos) + 10
        ws_permisos.cell(row=firma_row, column=2).value = "Director Colegio Los Alerces"
        ws_permisos.cell(row=firma_row + 2, column=2).value = "Puerto Montt, " + datetime.now().strftime("%d de %B de %Y")

        # Ajustar ancho de columnas
        for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']:
            ws_permisos.column_dimensions[col].width = 20

        # Respuesta HTTP
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        filename = f'DAEM_{year}_{int(mes):02d}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response

    def _exportar_daem3_excel(self, year, mes, tipo):
        """Exportar DAEM3 - Informe de Asistencia Laboral"""
        from asistencia.models import RegistroAsistencia

        # Determinar el tipo de personal
        if tipo in ['docentes', 'docente']:
            tipo_display = 'Docentes'
            # Filtrar por docentes
            funcionarios = CustomUser.objects.filter(
                role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO']
            ).order_by('first_name', 'last_name')
        else:  # asistentes
            tipo_display = 'Asistente de la Educación'
            # Filtrar por asistentes
            funcionarios = CustomUser.objects.filter(
                role__in=['FUNCIONARIO', 'SECRETARIA']
            ).order_by('first_name', 'last_name')

        # Obtener registros del mes
        registros_mes = RegistroAsistencia.objects.filter(
            fecha__year=int(year),
            fecha__month=int(mes),
            funcionario__in=funcionarios
        ).select_related('funcionario')

        # Agrupar por funcionario y calcular atrasos e inasistencias
        funcionarios_data = []
        for func in funcionarios:
            func_registros = registros_mes.filter(funcionario=func)

            # Calcular atrasos (acumulado mensual)
            total_atrasos = sum(r.minutos_retraso or 0 for r in func_registros if r.estado == 'RETRASO')

            # Calcular inasistencias injustificadas
            total_inasistencias = 0
            for r in func_registros:
                if r.estado == 'AUSENTE':
                    # Verificar si está justificado
                    tiene_justificacion = (
                        r.tiene_permiso_aprobado() or
                        r.tiene_licencia_medica() or
                        r.estado in ['JUSTIFICADO', 'DIA_ADMINISTRATIVO', 'LICENCIA_MEDICA']
                    )
                    if not tiene_justificacion:
                        total_inasistencias += 1

            # Solo incluir si tiene atrasos o inasistencias injustificadas
            if total_atrasos > 0 or total_inasistencias > 0:
                funcionarios_data.append({
                    'funcionario': func,
                    'atrasos': total_atrasos,
                    'inasistencias': total_inasistencias
                })

        # Crear Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Informe Asistencia Laboral"

        # Título
        ws['A1'] = "Informe Asistencia Laboral"
        ws['A1'].font = openpyxl.styles.Font(bold=True, size=14)
        ws.merge_cells('A1:D1')

        # Establecimiento
        ws['A3'] = "Establecimiento: Colegio Los Alerces"

        # Mes de Informe
        meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        ws['A5'] = f"Mes de Informe: {meses[int(mes)-1]}"

        # Tipo
        ws['A7'] = tipo_display

        # Encabezados de tabla
        headers = ['Nombre y Apellidos', 'RUN', 'Atrasos', 'Inasistencias']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=9, column=col)
            cell.value = header
            cell.font = openpyxl.styles.Font(bold=True)
            cell.border = openpyxl.styles.Border(
                left=openpyxl.styles.Side(style='thin'),
                right=openpyxl.styles.Side(style='thin'),
                top=openpyxl.styles.Side(style='thin'),
                bottom=openpyxl.styles.Side(style='thin')
            )
            cell.alignment = openpyxl.styles.Alignment(horizontal='center')

        # Datos
        for i, data in enumerate(funcionarios_data, 10):
            ws.cell(row=i, column=1).value = data['funcionario'].get_full_name() or data['funcionario'].username
            ws.cell(row=i, column=2).value = data['funcionario'].run
            ws.cell(row=i, column=3).value = data['atrasos']  # Minutos de atraso
            ws.cell(row=i, column=4).value = data['inasistencias']

            # Bordes para las celdas de datos
            for col in range(1, 5):
                cell = ws.cell(row=i, column=col)
                cell.border = openpyxl.styles.Border(
                    left=openpyxl.styles.Side(style='thin'),
                    right=openpyxl.styles.Side(style='thin'),
                    top=openpyxl.styles.Side(style='thin'),
                    bottom=openpyxl.styles.Side(style='thin')
                )

        # Firma
        firma_row = len(funcionarios_data) + 12
        ws.cell(row=firma_row, column=1).value = "Firma y Timbre Director"

        # Ajustar ancho de columnas
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 15

        # Respuesta HTTP
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        filename = f'Informe_Asistencia_Laboral_{tipo_display}_{year}_{int(mes):02d}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response


class ExportarDAEMPDFView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Exportar reporte DAEM/DAEM3 a PDF"""

    def test_func(self):
        return self.request.user.role in ['DIRECTOR', 'SECRETARIA', 'ADMIN', 'DIRECTIVO']

    def get(self, request):
        year = request.GET.get('year', '')
        mes = request.GET.get('mes', '')
        tipo = request.GET.get('tipo', '').lower()  # Para DAEM3, convertir a minúsculas

        # Si es DAEM3, mostrar formato de asistencia laboral
        if tipo in ['docentes', 'docente', 'asistentes', 'asistente']:
            return self._exportar_daem3_pdf(year, mes, tipo)

        # Formato regular DAEM (permisos administrativos)
        # Obtener funcionarios
        funcionarios = CustomUser.objects.filter(role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA', 'ADMIN']).order_by('first_name', 'last_name')

        # Preparar datos
        nomina_data = []
        for i, f in enumerate(funcionarios, 1):
            nomina_data.append({
                'numero': i,
                'nombre': f.get_full_name() or f.username,
                'run': f.run,
                'cargo': f.get_funcion_display() or ""
            })

        permisos_data = []
        permisos = SolicitudPermiso.objects.filter(estado='APROBADO', usuario__in=funcionarios).select_related('usuario').order_by('usuario__first_name', 'usuario__last_name', 'fecha_inicio')
        if year:
            permisos = permisos.filter(fecha_inicio__year=year)
        if mes:
            permisos = permisos.filter(fecha_inicio__month=mes)

        for i, p in enumerate(permisos, 1):
            permisos_data.append({
                'numero': i,
                'nombre': p.usuario.get_full_name() or p.usuario.username,
                'run': p.usuario.run,
                'cargo': p.usuario.get_funcion_display() or "",
                'tipo_permiso': "",
                'fecha_inicio': p.fecha_inicio.strftime("%d-%m-%Y") if p.fecha_inicio else "",
                'fecha_termino': p.fecha_termino.strftime("%d-%m-%Y") if p.fecha_termino else "",
                'cantidad_dias': float(p.dias_solicitados),
                'observaciones': ""
            })

        # Renderizar template HTML para PDF
        html_content = render_to_string('reportes/daem_pdf.html', {
            'nomina_data': nomina_data,
            'permisos_data': permisos_data,
            'year': year,
            'mes': mes,
            'fecha_actual': datetime.now(),
        })

        # Generar PDF
        pdf_file = HTML(string=html_content).write_pdf()

        # Crear respuesta HTTP
        response = HttpResponse(pdf_file, content_type='application/pdf')
        filename = f'DAEM_{year}_{int(mes):02d}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    def _exportar_daem3_pdf(self, year, mes, tipo):
        """Exportar DAEM3 - Informe de Asistencia Laboral"""
        from asistencia.models import RegistroAsistencia

        # Determinar el tipo de personal
        if tipo in ['docentes', 'docente']:
            tipo_display = 'Docentes'
            # Filtrar por docentes
            funcionarios = CustomUser.objects.filter(
                role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO']
            ).order_by('first_name', 'last_name')
        else:  # asistentes
            tipo_display = 'Asistente de la Educación'
            # Filtrar por asistentes
            funcionarios = CustomUser.objects.filter(
                role__in=['FUNCIONARIO', 'SECRETARIA']
            ).order_by('first_name', 'last_name')

        # Obtener registros del mes
        registros_mes = RegistroAsistencia.objects.filter(
            fecha__year=int(year),
            fecha__month=int(mes),
            funcionario__in=funcionarios
        ).select_related('funcionario')

        # Agrupar por funcionario y calcular atrasos e inasistencias
        funcionarios_data = []
        for func in funcionarios:
            func_registros = registros_mes.filter(funcionario=func)

            # Calcular atrasos (acumulado mensual en minutos)
            total_atrasos = sum(r.minutos_retraso or 0 for r in func_registros if r.estado == 'RETRASO')

            # Calcular inasistencias injustificadas
            total_inasistencias = 0
            for r in func_registros:
                if r.estado == 'AUSENTE':
                    # Verificar si está justificado
                    tiene_justificacion = (
                        r.tiene_permiso_aprobado() or
                        r.tiene_licencia_medica() or
                        r.estado in ['JUSTIFICADO', 'DIA_ADMINISTRATIVO', 'LICENCIA_MEDICA']
                    )
                    if not tiene_justificacion:
                        total_inasistencias += 1

            # Solo incluir si tiene atrasos o inasistencias injustificadas
            if total_atrasos > 0 or total_inasistencias > 0:
                funcionarios_data.append({
                    'funcionario': func,
                    'atrasos': total_atrasos,
                    'inasistencias': total_inasistencias
                })

        # Mes en texto
        meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        mes_texto = meses[int(mes)-1]

        # Renderizar template HTML para PDF
        html_content = render_to_string('reportes/daem3_pdf.html', {
            'titulo': 'Informe Asistencia Laboral',
            'establecimiento': 'Colegio Los Alerces',
            'mes_informe': mes_texto,
            'tipo_personal': tipo_display,
            'funcionarios': funcionarios_data,
            'fecha_actual': datetime.now(),
        })

        # Generar PDF
        pdf_file = HTML(string=html_content).write_pdf()

        # Crear respuesta HTTP
        response = HttpResponse(pdf_file, content_type='application/pdf')
        filename = f'Informe_Asistencia_Laboral_{tipo_display}_{year}_{int(mes):02d}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

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


class ExportarJustificacionesExcelView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Exportar Excel con justificaciones aprobadas"""

    def test_func(self):
        return self.request.user.role in ['DIRECTOR', 'SECRETARIA', 'ADMIN', 'DIRECTIVO']

    def get(self, request):
        year = request.GET.get('year', '')
        mes = request.GET.get('mes', '')

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Justificaciones Aprobadas"

        # Headers
        headers = ['N°', 'Nombre Completo', 'RUN', 'Cargo', 'Fecha', 'Tipo', 'Hora de Llegada', 'Estado Alegación', 'Revisado Por', 'Justificación Manual']
        ws.append(headers)

        # Column widths
        for col, width in [('A', 10), ('B', 25), ('C', 15), ('D', 20), ('E', 15), ('F', 15), ('G', 30), ('H', 20), ('I', 25)]:
            ws.column_dimensions[col].width = width

        # Query alegaciones aprobadas
        alegaciones = AlegacionAsistencia.objects.filter(
            estado='APROBADA'
        ).select_related(
            'registro_asistencia__funcionario',
            'revisado_por'
        )

        # Query justificaciones manuales (registros justificados por admin)
        justificaciones_manuales = RegistroAsistencia.objects.filter(
            justificado_por__isnull=False
        ).select_related('funcionario', 'justificado_por')

        if year:
            alegaciones = alegaciones.filter(registro_asistencia__fecha__year=year)
            justificaciones_manuales = justificaciones_manuales.filter(fecha__year=year)
        if mes:
            alegaciones = alegaciones.filter(registro_asistencia__fecha__month=mes)
            justificaciones_manuales = justificaciones_manuales.filter(fecha__month=mes)

        # Combinar y ordenar todas las justificaciones
        todas_justificaciones = []

        # Agregar alegaciones aprobadas
        for alegacion in alegaciones.order_by('registro_asistencia__fecha', 'registro_asistencia__funcionario__first_name'):
            reg = alegacion.registro_asistencia
            tipo = "Atraso" if reg.estado == 'RETRASO' else "Inasistencia" if reg.estado == 'AUSENTE' else reg.get_estado_display()

            todas_justificaciones.append({
                'tipo_justificacion': 'alegacion',
                'registro': reg,
                'alegacion': alegacion,
                'tipo': tipo,
                'hora_llegada': reg.hora_entrada_real.strftime('%H:%M') if reg.hora_entrada_real else '-',
                'estado': alegacion.get_estado_display(),
                'revisado_por': alegacion.revisado_por.get_full_name() if alegacion.revisado_por else "",
                'justificacion_manual': reg.justificacion_manual or ""
            })

        # Agregar justificaciones manuales
        for reg in justificaciones_manuales.order_by('fecha', 'funcionario__first_name'):
            tipo = "Atraso" if reg.estado == 'RETRASO' else "Inasistencia" if reg.estado == 'AUSENTE' else reg.get_estado_display()

            todas_justificaciones.append({
                'tipo_justificacion': 'manual',
                'registro': reg,
                'alegacion': None,
                'tipo': tipo,
                'hora_llegada': reg.hora_entrada_real.strftime('%H:%M') if reg.hora_entrada_real else '-',
                'estado': "Justificado Manualmente",
                'revisado_por': reg.justificado_por.get_full_name() if reg.justificado_por else "",
                'justificacion_manual': reg.justificacion_manual or ""
            })

        # Ordenar todas las justificaciones por fecha y nombre
        todas_justificaciones.sort(key=lambda x: (x['registro'].fecha, x['registro'].funcionario.first_name))

        for i, just in enumerate(todas_justificaciones, 1):
            reg = just['registro']

            ws.append([
                i,
                reg.funcionario.get_full_name() or reg.funcionario.username,
                reg.funcionario.run,
                reg.funcionario.get_funcion_display() or "",
                reg.fecha.strftime("%d-%m-%Y") if reg.fecha else "",
                just['tipo'],
                just['hora_llegada'],
                just['estado'],
                just['revisado_por'],
                just['justificacion_manual'][:100] + "..." if just['justificacion_manual'] and len(just['justificacion_manual']) > 100 else just['justificacion_manual'] or ""
            ])

        # Styling
        header_font = Font(bold=True, color="FFFFFF")
        fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = fill

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        filename = f"justificaciones_aprobadas"
        if mes and year:
            filename += f"_{mes}_{year}"
        elif year:
            filename += f"_{year}"
        response['Content-Disposition'] = f'attachment; filename={filename}.xlsx'

        wb.save(response)
        return response


class ExportarJustificacionesPDFView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Exportar PDF con justificaciones aprobadas"""

    def test_func(self):
        return self.request.user.role in ['DIRECTOR', 'SECRETARIA', 'ADMIN', 'DIRECTIVO']

    def get(self, request):
        year = request.GET.get('year', '')
        mes = request.GET.get('mes', '')

        # Query alegaciones aprobadas
        alegaciones = AlegacionAsistencia.objects.filter(
            estado='APROBADA'
        ).select_related(
            'registro_asistencia__funcionario',
            'revisado_por'
        )

        # Query justificaciones manuales (registros justificados por admin)
        justificaciones_manuales = RegistroAsistencia.objects.filter(
            justificado_por__isnull=False
        ).select_related('funcionario', 'justificado_por')

        if year:
            alegaciones = alegaciones.filter(registro_asistencia__fecha__year=year)
            justificaciones_manuales = justificaciones_manuales.filter(fecha__year=year)
        if mes:
            alegaciones = alegaciones.filter(registro_asistencia__fecha__month=mes)
            justificaciones_manuales = justificaciones_manuales.filter(fecha__month=mes)

        # Preparar datos para el template
        justificaciones = []

        # Agregar alegaciones aprobadas
        for alegacion in alegaciones.order_by('registro_asistencia__fecha', 'registro_asistencia__funcionario__first_name'):
            reg = alegacion.registro_asistencia
            tipo = "Atraso" if reg.estado == 'RETRASO' else "Inasistencia" if reg.estado == 'AUSENTE' else reg.get_estado_display()

            justificaciones.append({
                'nombre_completo': reg.funcionario.get_full_name() or reg.funcionario.username,
                'run': reg.funcionario.run,
                'cargo': reg.funcionario.get_funcion_display() or "",
                'fecha': reg.fecha.strftime("%d-%m-%Y") if reg.fecha else "",
                'tipo': tipo,
                'hora_llegada': reg.hora_entrada_real.strftime('%H:%M') if reg.hora_entrada_real else '-',
                'estado': alegacion.get_estado_display(),
                'revisado_por': alegacion.revisado_por.get_full_name() if alegacion.revisado_por else "",
                'justificacion_manual': reg.justificacion_manual[:200] + "..." if reg.justificacion_manual and len(reg.justificacion_manual) > 200 else reg.justificacion_manual or ""
            })

        # Agregar justificaciones manuales
        for reg in justificaciones_manuales.order_by('fecha', 'funcionario__first_name'):
            tipo = "Atraso" if reg.estado == 'RETRASO' else "Inasistencia" if reg.estado == 'AUSENTE' else reg.get_estado_display()

            justificaciones.append({
                'nombre_completo': reg.funcionario.get_full_name() or reg.funcionario.username,
                'run': reg.funcionario.run,
                'cargo': reg.funcionario.get_funcion_display() or "",
                'fecha': reg.fecha.strftime("%d-%m-%Y") if reg.fecha else "",
                'tipo': tipo,
                'hora_llegada': reg.hora_entrada_real.strftime('%H:%M') if reg.hora_entrada_real else '-',
                'estado': "Justificado Manualmente",
                'revisado_por': reg.justificado_por.get_full_name() if reg.justificado_por else "",
                'justificacion_manual': reg.justificacion_manual or ""
            })

        # Ordenar todas las justificaciones por fecha y nombre
        justificaciones.sort(key=lambda x: (x['fecha'], x['nombre_completo']))

        html_string = render_to_string('reportes/pdf_justificaciones.html', {
            'justificaciones': justificaciones,
            'fecha_exportacion': now().strftime('%d/%m/%Y %H:%M'),
            'year': year,
            'mes': mes
        })

        html = HTML(string=html_string)
        result = html.write_pdf()

        response = HttpResponse(content_type='application/pdf')
        filename = f"justificaciones_aprobadas"
        if mes and year:
            filename += f"_{mes}_{year}"
        elif year:
            filename += f"_{year}"
        response['Content-Disposition'] = f'inline; filename={filename}.pdf'
        response.write(result)
        return response




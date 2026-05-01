from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, FormView, ListView, View, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Avg, Sum
from django.http import HttpResponse
import openpyxl
from datetime import datetime, time, timedelta
from django.utils import timezone
from licencias.models import LicenciaMedica
from permisos.models import SolicitudPermiso
from .forms import EditarRegistroAsistenciaForm
import zipfile
import io
import re
import logging

# PDF generation
from weasyprint import HTML, CSS
from django.template.loader import render_to_string

# Import xlrd conditionally
try:
    import xlrd
    from xlrd import XLRDError
    XLRD_AVAILABLE = True
except ImportError:
    XLRD_AVAILABLE = False
    xlrd = None
    XLRDError = Exception

# Import pypdf for PDF processing (like payroll system)
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    pypdf = None
from .models import HorarioFuncionario, RegistroAsistencia, DiaFestivo, AlegacionAsistencia, AnoEscolar, DiaHorario, HorarioExcepcional
from .forms import CargaHorariosForm, HorarioFuncionarioForm, CargaRegistrosAsistenciaForm, DiaFestivoForm, HorarioExcepcionalForm
from django.shortcuts import get_object_or_404, redirect
from users.models import CustomUser
from core.utils import normalize_rut
from admin_dashboard.utils import registrar_log, get_client_ip

logger = logging.getLogger(__name__)


def find_user_by_rut(rut_encontrado: str):
    """
    Busca un usuario por RUT con matching inteligente que maneja múltiples formatos.
    """
    try:
        # Limpiar el RUT encontrado (remover espacios, mayúsculas)
        rut_limpio = rut_encontrado.upper().replace(' ', '').strip()

        # Crear diferentes variaciones para buscar
        variaciones_rut = set()

        # 1. RUT original limpio
        variaciones_rut.add(rut_limpio)

        # 2. RUT normalizado (con puntos)
        rut_normalizado = normalize_rut(rut_encontrado)
        variaciones_rut.add(rut_normalizado)

        # 3. RUT sin puntos
        rut_sin_puntos = rut_normalizado.replace('.', '')
        variaciones_rut.add(rut_sin_puntos)

        # 4. Si tiene puntos, intentar sin ellos
        if '.' in rut_limpio:
            variaciones_rut.add(rut_limpio.replace('.', ''))

        # 5. Si no tiene puntos pero tiene guión, intentar con puntos
        if '.' not in rut_limpio and '-' in rut_limpio:
            # Intentar agregar puntos automáticamente
            parts = rut_limpio.split('-')
            if len(parts) == 2:
                cuerpo, dv = parts
                cuerpo = cuerpo.replace('.', '')  # Remover puntos existentes si los hay

                if len(cuerpo) == 8:  # RUT de 8 dígitos: 12345678 -> 12.345.678
                    cuerpo_con_puntos = f"{cuerpo[:2]}.{cuerpo[2:5]}.{cuerpo[5:]}"
                    variaciones_rut.add(f"{cuerpo_con_puntos}-{dv}")
                elif len(cuerpo) == 7:  # RUT de 7 dígitos: 1234567 -> 1.234.567
                    cuerpo_con_puntos = f"{cuerpo[:1]}.{cuerpo[1:4]}.{cuerpo[4:]}"
                    variaciones_rut.add(f"{cuerpo_con_puntos}-{dv}")

        # Intentar cada variación
        for rut_variacion in variaciones_rut:
            try:
                user = CustomUser.objects.get(run=rut_variacion)
                logger.info(f"✅ RUT encontrado: '{rut_encontrado}' → '{rut_variacion}' ({user.get_full_name()})")
                return user
            except CustomUser.DoesNotExist:
                continue

        # Si ninguna variación funcionó, mostrar debug info
        logger.warning(f"❌ RUT '{rut_encontrado}' no encontrado. Variaciones probadas: {sorted(variaciones_rut)}")

        # Mostrar algunos RUTs de la base de datos para comparación
        sample_users = CustomUser.objects.all()[:10]
        logger.info(f"Muestra de RUTs en BD ({len(sample_users)} usuarios):")
        for i, user in enumerate(sample_users):
            logger.info(f"  {i+1}. RUT: '{user.run}' - Nombre: {user.get_full_name()}")

        # Mostrar todos los RUTs únicos en la BD para debugging
        all_runs = list(CustomUser.objects.values_list('run', flat=True).distinct())
        logger.info(f"Todos los RUTs en BD ({len(all_runs)}): {sorted(all_runs)}")

        # Buscar RUTs similares (primeros 8 dígitos)
        base_rut = rut_sin_puntos.replace('-', '')[:8]
        similar_users = CustomUser.objects.filter(run__icontains=base_rut)[:5]
        if similar_users:
            logger.info("RUTs similares encontrados:")
            for user in similar_users:
                logger.info(f"  '{user.run}' - {user.get_full_name()}")

        return None

    except Exception as e:
        logger.error(f"Error finding user by RUT {rut_encontrado}: {e}")
        return None


def load_data_file(archivo, mes=None, anio=None):
    """Carga datos de archivos Excel (.xlsx/.xls) o PDF y retorna filas de datos"""
    # Asegurar que el puntero del archivo esté al inicio
    if hasattr(archivo, 'seek'):
        archivo.seek(0)

    filename = archivo.name.lower()

    try:
        if filename.endswith(('.xlsx', '.xls')):
            # Procesar archivos Excel
            if filename.endswith('.xlsx'):
                # Usar openpyxl para .xlsx
                wb = openpyxl.load_workbook(archivo, data_only=True)
                ws = wb.active
                # Convertir a lista de filas
                rows = list(ws.iter_rows(min_row=2, values_only=True))
            elif filename.endswith('.xls'):
                # Intentar usar xlrd para .xls
                if not XLRD_AVAILABLE:
                    raise Exception("Los archivos .xls no son soportados actualmente. Por favor, convierta su archivo .xls a .xlsx usando Excel o Google Sheets y vuelva a intentarlo.")
                # Usar xlrd para .xls
                wb = xlrd.open_workbook(file_contents=archivo.read())
                ws = wb.sheet_by_index(0)  # Primera hoja
                # Convertir a lista de filas
                rows = [tuple(ws.cell_value(row_idx, col_idx) for col_idx in range(ws.ncols))
                       for row_idx in range(1, ws.nrows)]  # Skip header row

            return rows

        elif filename.endswith('.pdf'):
            # Procesar archivos PDF (similar al sistema de liquidaciones)
            if not PYPDF_AVAILABLE:
                raise Exception("Los archivos PDF no son soportados actualmente. Instale pypdf para habilitar esta funcionalidad.")

            # Extraer datos del PDF
            rows = []
            pdf_reader = pypdf.PdfReader(archivo)

            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if not text.strip():
                        continue

                    # Intentar extraer datos tabulares del texto
                    # Buscar patrones de asistencia: RUT, Nombre, Horario
                    lines = text.split('\n')

                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue

                        # Intentar parsear línea como datos de asistencia
                        # Formato esperado: "RUT, Nombre Horario"
                        # Ejemplo: "12345678-9, Juan Pérez 08:30-17:30"

                        # Buscar patrón: RUT seguido de coma, luego nombre, luego horario
                        match = re.match(r'^(\d{7,8}-[\dKk]|\d{1,2}\.\d{3}\.\d{3}-[\dKk]|\d{8,9})\s*,\s*(.+?)\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*-\s*\d{1,2}:\d{2}(?::\d{2})?)?)$', line)
                        if match:
                            rut = match.group(1).strip()
                            nombre = match.group(2).strip()
                            horario = match.group(3).strip()

                            # Parsear el horario (ej: "08:30-17:30" o solo "08:30")
                            horario_parts = horario.split('-')
                            hora_entrada_str = horario_parts[0].strip()
                            hora_salida_str = horario_parts[1].strip() if len(horario_parts) > 1 else None

                            # Para PDFs con formato "RUT, Nombre Horario", usamos la fecha del formulario
                            if mes and anio:
                                # Crear fecha del primer día del mes especificado
                                fecha_str = f"01/{mes:02d}/{anio}"
                            else:
                                fecha_str = datetime.now().strftime("%d/%m/%Y")

                            rows.append((rut, fecha_str, hora_entrada_str, hora_salida_str or ''))
                        else:
                            # Intentar otros formatos posibles
                            # Formato alternativo: RUT Nombre Horario (sin coma)
                            alt_match = re.match(r'^(\d{7,8}-[\dKk]|\d{1,2}\.\d{3}\.\d{3}-[\dKk]|\d{8,9})\s+(.+?)\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*-\s*\d{1,2}:\d{2}(?::\d{2})?)?)$', line)
                            if alt_match:
                                rut = alt_match.group(1).strip()
                                nombre = alt_match.group(2).strip()
                                horario = alt_match.group(3).strip()

                                horario_parts = horario.split('-')
                                hora_entrada_str = horario_parts[0].strip()
                                hora_salida_str = horario_parts[1].strip() if len(horario_parts) > 1 else None

                                # Usar fecha del formulario para este formato también
                                if mes and anio:
                                    fecha_str = f"01/{mes:02d}/{anio}"
                                else:
                                    fecha_str = datetime.now().strftime("%d/%m/%Y")

                                rows.append((rut, fecha_str, hora_entrada_str, hora_salida_str or ''))

                except Exception as e:
                    # Continuar con la siguiente página si hay error
                    continue

            if not rows:
                raise Exception("No se encontraron datos de asistencia en el archivo PDF. Asegúrese de que el PDF contenga información de asistencia en formato tabular o de texto estructurado.")

            return rows

        else:
            raise Exception("Formato de archivo no soportado. Use .xlsx, .xls o .pdf")

    except Exception as e:
        # Mejorar el manejo de errores para identificar el tipo de archivo
        error_msg = str(e)

        # Si es un error de Excel pero el archivo podría ser PDF
        if "File is not a zip file" in error_msg or "BadZipFile" in error_msg:
            # Intentar detectar si es un PDF mal etiquetado
            archivo.seek(0)
            first_bytes = archivo.read(8)
            if first_bytes.startswith(b'%PDF-'):
                raise Exception("El archivo parece ser un PDF pero tiene extensión .xls. Cambie la extensión a .pdf o use un archivo Excel válido.")
            else:
                raise Exception("El archivo no es un archivo Excel válido. Verifique que no esté corrupto.")

        # Si es un error de xlrd
        if "XLRDError" in str(type(e)) or "xlrd" in error_msg.lower():
            raise Exception(f"Error al leer el archivo Excel: {error_msg}")

        # Si es un error de PDF
        if "pdf" in error_msg.lower() or "PDF" in error_msg:
            raise Exception(f"Error al procesar el archivo PDF: {error_msg}")

        # Error genérico
        raise Exception(f"Error al procesar el archivo: {error_msg}")

class AsistenciaAdminView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Vista principal de administración de asistencia"""
    template_name = 'asistencia/admin_dashboard.html'

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Estadísticas generales
        total_funcionarios = CustomUser.objects.filter(role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA', 'ADMIN']).count()
        funcionarios_con_horario = HorarioFuncionario.objects.filter(activo=True).count()
        registros_hoy = RegistroAsistencia.objects.filter(fecha=datetime.now().date()).count()

        context.update({
            'total_funcionarios': total_funcionarios,
            'funcionarios_con_horario': funcionarios_con_horario,
            'registros_hoy': registros_hoy,
            'horarios_pendientes': total_funcionarios - funcionarios_con_horario,
        })

        return context


class GestionHorariosView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Vista para gestionar horarios de funcionarios"""
    template_name = 'asistencia/gestion_horarios.html'

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Búsqueda
        search = self.request.GET.get('search', '').strip()

        # Obtener todos los usuarios del sistema
        funcionarios = CustomUser.objects.filter(
            role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA', 'ADMIN']
        ).order_by('first_name', 'last_name')

        if search:
            from django.db.models import Q
            funcionarios = funcionarios.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(run__icontains=search)
            )

        # Agrupar todos los horarios activos en un diccionario (O(1) lookup)
        horarios_dict = {
            h.funcionario_id: h 
            for h in HorarioFuncionario.objects.filter(activo=True)
        }

        # Preparar datos con horarios
        funcionarios_data = []
        con_horario = 0
        sin_horario = 0

        for func in funcionarios:
            horario = horarios_dict.get(func.id)
            tiene_horario = horario is not None
            funcionarios_data.append({
                'funcionario': func,
                'horario': horario,
                'tiene_horario': tiene_horario,
            })

            if tiene_horario:
                con_horario += 1
            else:
                sin_horario += 1

        context['funcionarios_data'] = funcionarios_data
        context['total_con_horario'] = con_horario
        context['total_sin_horario'] = sin_horario
        context['search'] = search
        return context


class MiAsistenciaView(LoginRequiredMixin, TemplateView):
    """Vista para que usuarios vean su propia asistencia (todos los roles pueden ver la suya)"""
    template_name = 'asistencia/mi_asistencia.html'

    def get_context_data(self, **kwargs):
        from django.db.models import Count, Sum, Avg, Q
        from calendar import Calendar
        context = super().get_context_data(**kwargs)

        # Obtener parámetros de filtro
        mes = self.request.GET.get('mes')
        anio = self.request.GET.get('anio')

        if not mes or not anio:
            now = datetime.now()
            mes = str(now.month)
            anio = str(now.year)

        mes_int = int(mes)
        anio_int = int(anio)

        # Determinar si el funcionario es sereno
        es_sereno = self.request.user.funcion == 'SERENO'

        # Filtrar registros del usuario actual con select_related optimizado
        registros_qs = RegistroAsistencia.objects.filter(
            funcionario=self.request.user,
            fecha__year=anio,
            fecha__month=mes
        ).select_related('horario_asignado')

        # Indexar registros por fecha para acceso rápido
        registros_por_fecha = {}
        for registro in registros_qs:
            if registro.minutos_trabajados:
                registro.horas_trabajadas = round(registro.minutos_trabajados / 60, 1)
            else:
                registro.horas_trabajadas = None
            registro.detalle_permiso = None
            registros_por_fecha[registro.fecha] = registro

        # Consultar permisos administrativos aprobados para este mes
        from permisos.models import SolicitudPermiso
        from licencias.models import LicenciaMedica
        from datetime import timedelta as td

        primer_dia_mes = datetime(anio_int, mes_int, 1).date()
        ultimo_dia_mes = (primer_dia_mes + td(days=32)).replace(day=1) - td(days=1)

        permisos_qs = SolicitudPermiso.objects.filter(
            usuario=self.request.user,
            estado='APROBADO',
            fecha_inicio__lte=ultimo_dia_mes
        ).filter(
            Q(fecha_termino__gte=primer_dia_mes) | Q(fecha_termino__isnull=True)
        )

        # Construir dict de permisos por fecha
        permisos_por_fecha = {}
        for permiso in permisos_qs:
            inicio = max(permiso.fecha_inicio, primer_dia_mes)
            fin = permiso.fecha_termino or ultimo_dia_mes
            fin = min(fin, ultimo_dia_mes)
            d = inicio
            while d <= fin:
                permisos_por_fecha[d] = permiso
                d += td(days=1)

        # Consultar licencias médicas para este mes
        licencias_qs = LicenciaMedica.objects.filter(
            usuario=self.request.user,
            fecha_inicio__lte=ultimo_dia_mes
        )

        licencias_por_fecha = {}
        for licencia in licencias_qs:
            fin_lic = licencia.fecha_inicio + td(days=licencia.dias - 1)
            inicio = max(licencia.fecha_inicio, primer_dia_mes)
            fin = min(fin_lic, ultimo_dia_mes)
            d = inicio
            while d <= fin:
                licencias_por_fecha[d] = licencia
                d += td(days=1)

        # Generar estructura de calendario mensual
        cal = Calendar(firstweekday=0)  # Lunes como primer día
        semanas_calendario = []

        # Obtener días festivos del mes
        festivos = set(
            DiaFestivo.objects.filter(
                fecha__year=anio_int,
                fecha__month=mes_int
            ).values_list('fecha', flat=True)
        )

        ESTADO_DISPLAY = {
            'DIA_ADMINISTRATIVO': 'Día Administrativo',
            'MEDIO_DIA': 'Medio Día Administrativo',
            'LICENCIA_MEDICA': 'Licencia Médica',
        }

        class RegistroVirtual:
            """Registro virtual para días con permiso/licencia sin marcación"""
            def __init__(self, estado):
                self.estado = estado
                self.minutos_retraso = 0
                self.hora_entrada_real = None
                self.hora_salida_real = None
                self.minutos_trabajados = None
                self.horas_trabajadas = None
                self.horario_asignado = None
                self.alegacion = None
                self._estado_display = ESTADO_DISPLAY.get(estado, estado)
            @property
            def pk(self):
                return None
            def get_estado_display(self):
                return self._estado_display

        for semana in cal.monthdayscalendar(anio_int, mes_int):
            dias_semana = []
            for dia_num in semana:
                if dia_num == 0:
                    dias_semana.append(None)
                else:
                    fecha = datetime(anio_int, mes_int, dia_num).date()
                    dia_semana = fecha.weekday()  # 0=Lunes, 6=Domingo
                    es_fin_de_semana = dia_semana >= 5
                    es_festivo = fecha in festivos
                    registro = registros_por_fecha.get(fecha)
                    today = datetime.now().date()
                    es_pasado = fecha < today
                    es_hoy = fecha == today
                    es_dia_escolar = AnoEscolar.es_dia_escolar(fecha)

                    # Crear registro virtual si hay permiso/licencia
                    # Reemplaza registros AUSENTE retroactivamente
                    if fecha in licencias_por_fecha:
                        if not registro or registro.estado == 'AUSENTE':
                            registro = RegistroVirtual('LICENCIA_MEDICA')
                    elif fecha in permisos_por_fecha:
                        permiso = permisos_por_fecha[fecha]
                        if not registro or registro.estado == 'AUSENTE':
                            if permiso.dias_solicitados == 0.5:
                                registro = RegistroVirtual('MEDIO_DIA')
                            else:
                                registro = RegistroVirtual('DIA_ADMINISTRATIVO')

                    # No es falta si hay registro (real o virtual), festivo, o no es día escolar
                    # O si la fecha es anterior a su ingreso al establecimiento
                    es_posterior_a_ingreso = fecha >= self.request.user.date_joined.date()
                    es_falta_sin_registro = es_pasado and not registro and not es_festivo and es_dia_escolar and es_posterior_a_ingreso

                    # Los fines de semana solo aplican para serenos
                    if es_fin_de_semana and not es_sereno:
                        dias_semana.append({
                            'dia': dia_num,
                            'fecha': fecha,
                            'es_fin_de_semana': True,
                            'es_festivo': es_festivo,
                            'es_sereno': False,
                            'registro': None,
                            'es_laboral': False,
                            'es_hoy': es_hoy,
                            'es_falta_sin_registro': False,
                            'es_dia_escolar': es_dia_escolar,
                        })
                        continue

                    dias_semana.append({
                        'dia': dia_num,
                        'fecha': fecha,
                        'es_fin_de_semana': es_fin_de_semana,
                        'es_festivo': es_festivo,
                        'es_sereno': es_sereno,
                        'registro': registro,
                        'es_laboral': True,
                        'es_hoy': es_hoy,
                        'es_falta_sin_registro': es_falta_sin_registro,
                        'es_dia_escolar': es_dia_escolar,
                    })
            semanas_calendario.append(dias_semana)

        # Estadísticas del período
        registros_list = list(registros_por_fecha.values())

        # Incluir registros virtuales (permisos/licencias sin marcación)
        registros_virtuales = []
        for semana in semanas_calendario:
            for dia in semana:
                if dia and dia.get('registro') and isinstance(dia['registro'], RegistroVirtual):
                    registros_virtuales.append(dia['registro'])

        todos_registros = registros_list + registros_virtuales

        faltas_sin_registro = sum(
            1 for semana in semanas_calendario for dia in semana
            if dia and dia.get('es_falta_sin_registro')
        )
        stats = {
            'total': len(todos_registros),
            'puntuales': sum(1 for r in todos_registros if r.estado == 'PUNTUAL'),
            'retraso': sum(1 for r in todos_registros if r.estado == 'RETRASO'),
            'ausente': sum(1 for r in todos_registros if r.estado == 'AUSENTE') + faltas_sin_registro,
            'medio_dia': sum(1 for r in todos_registros if r.estado == 'MEDIO_DIA'),
            'admin': sum(1 for r in todos_registros if r.estado == 'DIA_ADMINISTRATIVO'),
            'licencia': sum(1 for r in todos_registros if r.estado == 'LICENCIA_MEDICA'),
            'sin_marcacion': sum(1 for r in todos_registros if r.estado == 'SIN_MARCACION_ENTRADA'),
            'dias_con_tiempo': sum(1 for r in registros_list if r.minutos_trabajados is not None),
            'tiempo_promedio': (sum(r.minutos_trabajados for r in registros_list if r.minutos_trabajados is not None) / max(1, sum(1 for r in registros_list if r.minutos_trabajados is not None))),
            'total_minutos_trabajados': sum(r.minutos_trabajados or 0 for r in registros_list),
            'total_minutos_retraso': sum(r.minutos_retraso for r in registros_list if r.minutos_retraso > 0),
        }

        total_dias = stats['total'] or 0
        dias_puntuales = stats['puntuales'] or 0
        total_minutos_retraso_mes = stats['total_minutos_retraso'] or 0
        total_horas_trabajadas_mes = round((stats['total_minutos_trabajados'] or 0) / 60, 1)

        # Horas semanales
        horas_semanales = {}
        for i, semana in enumerate(semanas_calendario):
            minutos_semana = 0
            for d in semana:
                if d and d['registro'] and d['registro'].minutos_trabajados:
                    minutos_semana += d['registro'].minutos_trabajados
            if minutos_semana > 0:
                horas_semanales[f"Semana {i + 1}"] = round(minutos_semana / 60, 1)

        # Meses y años disponibles
        context['meses'] = [
            (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
            (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
            (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
        ]
        anios_con_registros = list(RegistroAsistencia.objects.filter(
            funcionario=self.request.user
        ).values_list('fecha__year', flat=True).distinct().order_by('-fecha__year'))
        
        # Si no hay registros, mostrar años por defecto (actual y anterior)
        if not anios_con_registros:
            from datetime import datetime as dt
            anio_actual = dt.now().year
            anios_con_registros = [anio_actual, anio_actual - 1]
        
        context['anios_disponibles'] = anios_con_registros

        # Horario asignado
        horario_actual = HorarioFuncionario.objects.filter(
            funcionario=self.request.user, activo=True
        ).first()

        # Generar horario_semanal
        horario_semanal = []
        dias_totales = 7 if es_sereno else 5
        total_minutos_semanales = 0

        DIA_CHOICES_DICT = {
            0: 'Lunes', 1: 'Martes', 2: 'Miércoles',
            3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'
        }

        dias_configurados = {}
        if horario_actual:
            for dh in horario_actual.dias.all():
                dias_configurados[dh.dia_semana] = dh

        for i in range(dias_totales):
            dia_obj = dias_configurados.get(i)
            if dia_obj:
                horas = 0
                if dia_obj.activo and dia_obj.hora_entrada and dia_obj.hora_salida:
                    min1 = dia_obj.hora_entrada.hour * 60 + dia_obj.hora_entrada.minute
                    min2 = dia_obj.hora_salida.hour * 60 + dia_obj.hora_salida.minute
                    if min2 < min1: min2 += 24 * 60
                    horas = (min2 - min1) / 60
                    total_minutos_semanales += (min2 - min1)
                horario_semanal.append({
                    'dia_semana': i,
                    'nombre': DIA_CHOICES_DICT[i],
                    'activo': dia_obj.activo,
                    'hora_entrada': dia_obj.hora_entrada.strftime('%H:%M') if dia_obj.hora_entrada else '',
                    'hora_salida': dia_obj.hora_salida.strftime('%H:%M') if dia_obj.hora_salida else '',
                    'horas_asignadas': round(horas, 1)
                })
            else:
                horas = 0
                if horario_actual and horario_actual.hora_entrada:
                    min1 = horario_actual.hora_entrada.hour * 60 + horario_actual.hora_entrada.minute
                    min2 = 17 * 60 # Default 17:00
                    if min2 < min1: min2 += 24 * 60
                    horas = (min2 - min1) / 60
                    total_minutos_semanales += (min2 - min1)
                horario_semanal.append({
                    'dia_semana': i,
                    'nombre': DIA_CHOICES_DICT[i],
                    'activo': True,
                    'hora_entrada': horario_actual.hora_entrada.strftime('%H:%M') if horario_actual and horario_actual.hora_entrada else '08:00',
                    'hora_salida': '17:00',
                    'horas_asignadas': round(horas, 1)
                })

        total_horas_semanales = f"{total_minutos_semanales // 60}h {total_minutos_semanales % 60}m" if total_minutos_semanales % 60 != 0 else f"{total_minutos_semanales // 60}h"

        # Calcular horas esperadas para el mes completo (según horario configurado)
        total_minutos_esperados_mes = 0
        from calendar import Calendar
        cal = Calendar(firstweekday=0)
        for semana in cal.monthdayscalendar(anio_int, mes_int):
            for dia_num in semana:
                if dia_num != 0:
                    fecha = datetime(anio_int, mes_int, dia_num).date()
                    if fecha in festivos:
                        continue
                    
                    dia_semana = fecha.weekday()
                    if not es_sereno and dia_semana >= 5:
                        continue
                        
                    dia_h = next((d for d in horario_semanal if d['dia_semana'] == dia_semana), None)
                    if dia_h and dia_h['activo']:
                        if dia_h['hora_entrada'] and dia_h['hora_salida']:
                            h1, m1 = map(int, dia_h['hora_entrada'].split(':'))
                            h2, m2 = map(int, dia_h['hora_salida'].split(':'))
                            min1 = h1 * 60 + m1
                            min2 = h2 * 60 + m2
                            if min2 < min1: min2 += 24 * 60
                            total_minutos_esperados_mes += (min2 - min1)

        total_horas_esperadas_mes = round(total_minutos_esperados_mes / 60, 1)

        context.update({
            'registros': registros_list,
            'semanas_calendario': semanas_calendario,
            'es_sereno': es_sereno,
            'mes': mes,
            'mes_int': mes_int,
            'anio': anio,
            'anio_int': anio_int,
            'today': datetime.now().date(),
            'ano_escolar_activo': AnoEscolar.get_activo(),
            'horario_semanal': horario_semanal,
            'total_horas_semanales': total_horas_semanales,
            'estadisticas': {
                'total_dias': total_dias,
                'dias_puntuales': dias_puntuales,
                'dias_retraso': stats['retraso'] or 0,
                'dias_ausente': stats['ausente'] or 0,
                'dias_medio_dia': stats['medio_dia'] or 0,
                'dias_admin': stats['admin'] or 0,
                'dias_licencia': stats['licencia'] or 0,
                'porcentaje_puntualidad': round((dias_puntuales / total_dias * 100) if total_dias > 0 else 0, 1),
                'dias_con_tiempo_trabajado': stats['dias_con_tiempo'] or 0,
                'tiempo_promedio_trabajado': round(stats['tiempo_promedio'] or 0, 0),
                'total_horas_trabajadas_mes': total_horas_trabajadas_mes,
                'total_horas_esperadas_mes': total_horas_esperadas_mes,
                'total_minutos_retraso_mes': total_minutos_retraso_mes,
                'horas_semanales': horas_semanales,
            }
        })

        return context

class CargaHorariosView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Vista para cargar archivos Excel de registros de asistencia (marcaciones)"""
    template_name = "asistencia/carga_horarios.html"
    form_class = CargaHorariosForm
    success_url = "/asistencia/cargar-horarios/"

    def test_func(self):
        return self.request.user.role in ["ADMIN", "SECRETARIA"]

    def form_valid(self, form):
        archivo_excel = form.cleaned_data["archivo_excel"]

        try:
            registros_creados, errores = self.procesar_excel_asistencia(archivo_excel)

            if registros_creados > 0:
                messages.success(
                    self.request,
                    f"Se procesaron correctamente {registros_creados} registros de asistencia."
                )
                registrar_log(
                    usuario=self.request.user,
                    tipo='IMPORT',
                    accion='Carga Masiva de Asistencia',
                    descripcion=f'Se cargaron {registros_creados} registros desde Excel',
                    ip_address=get_client_ip(self.request)
                )
            else:
                messages.warning(self.request, "No se encontraron registros válidos para procesar.")

            if errores:
                for error in errores[:8]:
                    messages.warning(self.request, error)
                if len(errores) > 8:
                    messages.warning(self.request, f"... y {len(errores) - 8} errores más.")

        except Exception as e:
            messages.error(self.request, f"Error al procesar el archivo: {str(e)}")
            return self.form_invalid(form)

        return super().form_valid(form)

    def procesar_excel_asistencia(self, archivo_excel):
        """Procesa Excel con formato: RUT, Nombre, DD-MM-YYYY HH:MM"""
        rows = load_data_file(archivo_excel, None, None)

        registros_creados = 0
        errores = []
        datos_agrupados = {}  # {(rut, fecha): [hora1, hora2, ...]}

        # Primera pasada: agrupar por (rut, fecha)
        for row_num, row in enumerate(rows, start=2):
            if not any(row):
                continue

            try:
                if len(row) < 3:
                    continue

                rut_raw = row[0]
                if not rut_raw:
                    errores.append(f"Fila {row_num}: Falta RUT")
                    continue

                rut_str = str(rut_raw).strip()

                # Formato: RUT, Nombre, "DD-MM-YYYY HH:MM"
                horario_raw = row[2]
                horario_str = str(horario_raw).strip()

                # Intentar parsear fecha+hora
                fecha = None
                hora = None

                # Formato "DD-MM-YYYY HH:MM"
                match = re.match(r'^(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}):(\d{2})$', horario_str)
                if match:
                    dia, mes_num, anio_num = match.groups()[:3]
                    hora_str, minuto_str = match.groups()[3:]
                    fecha = datetime(int(anio_num), int(mes_num), int(dia)).date()
                    hora = time(int(hora_str), int(minuto_str))
                else:
                    # Intentar formato datetime de Excel
                    if isinstance(horario_raw, datetime):
                        fecha = horario_raw.date()
                        hora = horario_raw.time()
                    else:
                        # Intentar otros formatos comunes
                        formatos_fecha = ["%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M:%S"]
                        for fmt in formatos_fecha:
                            try:
                                dt = datetime.strptime(horario_str, fmt)
                                fecha = dt.date()
                                hora = dt.time()
                                break
                            except ValueError:
                                continue

                if not fecha or not hora:
                    errores.append(f"Fila {row_num}: Formato inválido '{horario_str}'")
                    continue

                key = (rut_str, fecha)
                if key not in datos_agrupados:
                    datos_agrupados[key] = []
                datos_agrupados[key].append(hora)

            except Exception as e:
                errores.append(f"Fila {row_num}: Error - {str(e)}")

        # Segunda pasada: crear registros
        for (rut_str, fecha), horas in datos_agrupados.items():
            try:
                funcionario = find_user_by_rut(rut_str)
                if not funcionario:
                    errores.append(f"RUT {rut_str} no encontrado")
                    continue

                horas_ordenadas = sorted(horas)
                hora_entrada = None
                hora_salida = None

                # Separar horas en bloques para distinguir turnos nocturnos de entradas tempranas:
                # - madrugada (0-4h): podría ser salida de turno nocturno previo O entrada muy temprana
                # - mañana (5-11h): entradas diurnas reales (incluye entradas antes de las 7:30)
                # - tarde (12-23h): salidas diurnas
                horas_madrugada = [h for h in horas_ordenadas if h.hour < 5]
                horas_manana    = [h for h in horas_ordenadas if 5 <= h.hour < 12]
                horas_tarde     = [h for h in horas_ordenadas if h.hour >= 12]

                if horas_manana:
                    # Hay entrada diurna real → tomar la primera (puede ser antes de las 7:30)
                    hora_entrada = horas_manana[0]
                    # Si además hay madrugada, es una salida de turno nocturno previo (no es entrada)
                else:
                    # No hay mañana: la madrugada es la entrada real (turno muy temprano)
                    if horas_madrugada:
                        hora_entrada = horas_madrugada[0]

                if horas_tarde:
                    hora_salida = horas_tarde[-1]

                registro, created = RegistroAsistencia.objects.get_or_create(
                    funcionario=funcionario,
                    fecha=fecha,
                    defaults={
                        'hora_entrada_real': hora_entrada,
                        'hora_salida_real': hora_salida,
                        'procesado_por': self.request.user,
                    }
                )
                if not created:
                    registro.hora_entrada_real = hora_entrada
                    registro.hora_salida_real = hora_salida
                    registro.procesado_por = self.request.user
                    registro.save()

                registros_creados += 1

            except Exception as e:
                errores.append(f"Error {rut_str} {fecha}: {str(e)}")

        return registros_creados, errores


class GestionAsistenciaView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Vista administrativa para gestionar usuarios con asistencia (similar a gestion_liquidaciones pero mostrando usuarios)"""
    model = CustomUser
    template_name = 'asistencia/gestion_asistencia.html'
    context_object_name = 'usuarios'
    paginate_by = 20

    def get_paginate_by(self, queryset):
        """Permite cambiar dinámicamente el número de elementos por página"""
        paginate_by = self.request.GET.get('paginate_by', '20')
        if paginate_by == 'todos':
            return None  # Sin paginación
        try:
            return int(paginate_by)
        except ValueError:
            return 20  # Valor por defecto

    def test_func(self):
        # Solo administradores, secretarias, directores y directivos pueden ver la gestión
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def get_queryset(self):
        # Obtener todos los usuarios del sistema
        queryset = CustomUser.objects.filter(
            is_active=True,
            role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA', 'ADMIN']
        )

        # Filtros de búsqueda
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(run__icontains=search)
            )

        # Ordenamiento — por defecto: nombre ascendente
        sort_by = self.request.GET.get('sort', 'name')

        if sort_by == 'name':
            queryset = queryset.order_by('first_name', 'last_name')
        elif sort_by == 'name_desc':
            queryset = queryset.order_by('-first_name', '-last_name')
        elif sort_by == 'rut':
            queryset = queryset.order_by('run')
        elif sort_by == 'rut_desc':
            queryset = queryset.order_by('-run')
        elif sort_by == 'role':
            queryset = queryset.order_by('role', 'first_name', 'last_name')
        elif sort_by == 'role_desc':
            queryset = queryset.order_by('-role', 'first_name', 'last_name')
        else:
            queryset = queryset.order_by('first_name', 'last_name')

        return queryset

    def get_context_data(self, **kwargs):
        from django.db.models import Count, Q
        context = super().get_context_data(**kwargs)

        # Estadísticas generales - UNA sola query
        stats = RegistroAsistencia.objects.aggregate(
            total_registros=Count('id'),
            registros_puntuales=Count('id', filter=Q(estado='PUNTUAL')),
            registros_retraso=Count('id', filter=Q(estado='RETRASO')),
            registros_ausentes=Count('id', filter=Q(estado='AUSENTE')),
            total_usuarios=Count('funcionario_id', distinct=True),
        )

        context['estadisticas'] = {
            'total_usuarios': stats['total_usuarios'] or 0,
            'total_registros': stats['total_registros'] or 0,
            'registros_puntuales': stats['registros_puntuales'] or 0,
            'registros_retraso': stats['registros_retraso'] or 0,
            'registros_ausentes': stats['registros_ausentes'] or 0,
            'porcentaje_puntualidad': round(
                (stats['registros_puntuales'] / stats['total_registros'] * 100)
                if stats['total_registros'] > 0 else 0, 1
            )
        }

        # Obtener registros de una sola consulta (bulk mapping) en lugar de N queries
        usuario_ids = [u.id for u in context['usuarios']]
        registros_totales = RegistroAsistencia.objects.filter(funcionario_id__in=usuario_ids)
        
        # Mapear estadísticas por usuario
        stats_por_usuario = {}
        for r in registros_totales:
            uid = r.funcionario_id
            if uid not in stats_por_usuario:
                stats_por_usuario[uid] = {'total': 0, 'puntuales': 0, 'ultimo_registro': None}
            
            stats_por_usuario[uid]['total'] += 1
            if r.estado == 'PUNTUAL':
                stats_por_usuario[uid]['puntuales'] += 1
            
            if not stats_por_usuario[uid]['ultimo_registro'] or r.fecha > stats_por_usuario[uid]['ultimo_registro'].fecha:
                stats_por_usuario[uid]['ultimo_registro'] = r
        

        # Para cada usuario, agregar estadísticas pre-calculadas
        usuarios_con_stats = []
        for usuario in context['usuarios']:
            user_stats = stats_por_usuario.get(usuario.id, {'total': 0, 'puntuales': 0, 'ultimo_registro': None})
            
            total_registros_usuario = user_stats['total']
            registros_puntuales_usuario = user_stats['puntuales']
            ultimo_registro = user_stats['ultimo_registro']

            usuarios_con_stats.append({
                'usuario': usuario,
                'total_registros': total_registros_usuario,
                'registros_puntuales': registros_puntuales_usuario,
                'porcentaje_puntualidad': round((registros_puntuales_usuario / total_registros_usuario * 100) if total_registros_usuario > 0 else 0, 1),
                'ultimo_registro': ultimo_registro.fecha if ultimo_registro else None,
            })

        # Ordenar usuarios con estadísticas
        sort_by = self.request.GET.get('sort', 'name')

        if sort_by == 'name':
            usuarios_con_stats.sort(key=lambda x: (x['usuario'].first_name, x['usuario'].last_name))
        elif sort_by == 'name_desc':
            usuarios_con_stats.sort(key=lambda x: (x['usuario'].first_name, x['usuario'].last_name), reverse=True)
        elif sort_by == 'rut':
            usuarios_con_stats.sort(key=lambda x: x['usuario'].run or '')
        elif sort_by == 'rut_desc':
            usuarios_con_stats.sort(key=lambda x: x['usuario'].run or '', reverse=True)
        elif sort_by == 'registros':
            usuarios_con_stats.sort(key=lambda x: x['total_registros'])
        elif sort_by == 'registros_desc':
            usuarios_con_stats.sort(key=lambda x: x['total_registros'], reverse=True)
        elif sort_by == 'puntualidad':
            usuarios_con_stats.sort(key=lambda x: x['porcentaje_puntualidad'])
        elif sort_by == 'puntualidad_desc':
            usuarios_con_stats.sort(key=lambda x: x['porcentaje_puntualidad'], reverse=True)
        elif sort_by == 'ultimo_acceso':
            usuarios_con_stats.sort(key=lambda x: x['ultimo_registro'] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        elif sort_by == 'ultimo_acceso_desc':
            usuarios_con_stats.sort(key=lambda x: x['ultimo_registro'] or datetime.min.replace(tzinfo=timezone.utc))

        context['usuarios_con_stats'] = usuarios_con_stats

        # Filtros aplicados
        context['filtros_aplicados'] = {
            'search': self.request.GET.get('search', ''),
        }
        context['current_sort'] = sort_by
        context['paginate_by'] = self.request.GET.get('paginate_by', '20')

        return context


class CargaRegistrosAsistenciaView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Vista para cargar registros de asistencia desde vouchers del reloj control"""
    template_name = "asistencia/carga_registros.html"
    form_class = CargaRegistrosAsistenciaForm
    success_url = "/asistencia/gestion/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'carga_resultado' in self.request.session:
            context['resultado'] = self.request.session.pop('carga_resultado')
        return context

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

    def form_valid(self, form):
        archivo_excel = form.cleaned_data["archivo_excel"]
        mes = form.cleaned_data.get("mes")
        anio = form.cleaned_data.get("anio")

        try:
            # Procesar el archivo
            registros_creados, errores = self.procesar_excel_asistencia(archivo_excel, mes, anio)

            # Guardar resultados para mostrar en el template de forma elegante
            self.request.session['carga_resultado'] = {
                'success_count': registros_creados,
                'error_count': len(errores),
                'errors': errores[:10],  # Mostrar máximo 10 errores de muestra
            }

            if registros_creados > 0:
                messages.success(self.request, "Proceso de carga finalizado.")
                registrar_log(
                    usuario=self.request.user,
                    tipo='IMPORT',
                    accion='Carga Masiva de Asistencia',
                    descripcion=f'Se cargaron {registros_creados} registros de asistencia desde reloj control',
                    ip_address=get_client_ip(self.request)
                )
            elif not errores:
                messages.warning(self.request, "No se encontraron registros válidos para procesar.")

        except Exception as e:
            messages.error(self.request, f"Error al procesar el archivo: {str(e)}")
            return self.form_invalid(form)

        return super().form_valid(form)

    def procesar_excel_asistencia(self, archivo_excel, mes=None, anio=None):
        """Procesa el archivo Excel de registros del reloj control con soporte para múltiples formatos de fecha y hora.
        Soporta entradas tempranas (antes de las 7:30 AM) separando madrugada de mañana."""
        logger.info(f"Iniciando procesamiento de archivo Excel de asistencia. Usuario: {self.request.user.get_full_name()}")

        rows = load_data_file(archivo_excel, mes, anio)
        logger.info(f"Archivo cargado: {len(rows)} filas encontradas")

        registros_creados = 0
        errores = []
        ruts_no_encontrados = 0

        def parse_date(value):
            """Parse date from various formats"""
            if not value:
                return None

            # Si ya es un objeto date/datetime
            if hasattr(value, 'date'):
                return value.date()
            if hasattr(value, 'year'):
                return value.date()

            # Convertir a string para parsing
            value_str = str(value).strip()

            # Formatos de fecha comunes
            formatos_fecha = [
                "%d/%m/%Y",  # 25/12/2024
                "%d-%m-%Y",  # 25-12-2024
                "%Y/%m/%d",  # 2024/12/25
                "%Y-%m-%d",  # 2024-12-25
                "%m/%d/%Y",  # 12/25/2024
                "%d/%m/%y",  # 25/12/24
                "%Y%m%d",    # 20241225
            ]

            for formato in formatos_fecha:
                try:
                    return datetime.strptime(value_str, formato).date()
                except ValueError:
                    continue

            # Intentar con números seriales de Excel (días desde 1900-01-01)
            try:
                if isinstance(value, (int, float)) and value > 40000:  # Fechas de Excel comienzan ~1900
                    from datetime import timedelta
                    excel_epoch = datetime(1900, 1, 1)
                    return (excel_epoch + timedelta(days=int(value) - 2)).date()  # -2 por bug de Excel
            except:
                pass

            return None

        def parse_time(value):
            """Parse time from various formats"""
            if not value:
                return None

            # Si ya es un objeto time/datetime
            if hasattr(value, 'time'):
                return value.time()
            if hasattr(value, 'hour') and hasattr(value, 'minute'):
                return time(value.hour, value.minute, value.second if hasattr(value, 'second') else 0)

            # Convertir a string para parsing
            value_str = str(value).strip()

            # Formatos de hora comunes
            formatos_hora = [
                "%H:%M:%S",  # 08:30:00
                "%H:%M",     # 08:30
                "%I:%M:%S %p",  # 08:30:00 AM
                "%I:%M %p",    # 08:30 AM
            ]

            for formato in formatos_hora:
                try:
                    parsed = datetime.strptime(value_str, formato)
                    return parsed.time()
                except ValueError:
                    continue

            # Intentar con números decimales (horas como 8.5 = 8:30)
            try:
                if isinstance(value, (int, float)):
                    hours = int(value)
                    minutes = int((value - hours) * 60)
                    return time(hours, minutes)
            except:
                pass

            # Intentar extraer horas y minutos de strings complejos
            import re
            match = re.search(r'(\d{1,2}):(\d{2})', value_str)
            if match:
                try:
                    return time(int(match.group(1)), int(match.group(2)))
                except:
                    pass

            return None

        # Primero, recolectar todos los datos agrupados por RUT y fecha
        datos_agrupados = {}  # {(rut, fecha): [hora1, hora2, ...]}

        ruts_unicos_en_archivo = set()
        ruts_no_encontrados_set = set()

        for row_num, row in enumerate(rows, start=2):
            if not any(row):  # Skip empty rows
                continue

            try:
                if len(row) < 3:
                    errores.append(f"Fila {row_num}: Se requieren al menos 3 columnas (RUT, Nombre, Fecha/Horario)")
                    continue

                rut_raw = row[0] if len(row) > 0 else None
                nombre = row[1] if len(row) > 1 else None

                if not rut_raw:
                    errores.append(f"Fila {row_num}: Falta RUT obligatorio")
                    continue

                # Convertir RUT a string para procesamiento consistente
                rut_str = str(rut_raw).strip()
                ruts_unicos_en_archivo.add(rut_str)

                # Detectar formato y extraer fecha y hora
                fecha = None
                hora = None

                if len(row) >= 5:
                    # Formato extendido: RUT, Nombre, Fecha, Hora_AM, Hora_PM
                    fecha_raw = row[2] if len(row) > 2 else None
                    hora_am_raw = row[3] if len(row) > 3 else None
                    hora_pm_raw = row[4] if len(row) > 4 else None

                    fecha = parse_date(fecha_raw)
                    if not fecha:
                        errores.append(f"Fila {row_num}: Fecha inválida '{fecha_raw}'")
                        continue

                    # Agregar horas AM y PM por separado si existen
                    if hora_am_raw:
                        hora_am = parse_time(hora_am_raw)
                        if hora_am:
                            key = (rut_str, fecha)
                            if key not in datos_agrupados:
                                datos_agrupados[key] = []
                            datos_agrupados[key].append(hora_am)

                    if hora_pm_raw:
                        hora_pm = parse_time(hora_pm_raw)
                        if hora_pm:
                            key = (rut_str, fecha)
                            if key not in datos_agrupados:
                                datos_agrupados[key] = []
                            datos_agrupados[key].append(hora_pm)

                elif len(row) >= 3:
                    # Formato original: RUT, Nombre, "DD-MM-YYYY HH:MM"
                    horario_raw = row[2]
                    horario_str = str(horario_raw).strip()

                    # Intentar extraer fecha y hora del formato "DD-MM-YYYY HH:MM"
                    fecha_hora_match = re.match(r'^(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}):(\d{2})$', horario_str)
                    if fecha_hora_match:
                        dia, mes_num, anio_num = fecha_hora_match.groups()[:3]
                        hora_str, minuto_str = fecha_hora_match.groups()[3:]

                        try:
                            fecha = datetime(int(anio_num), int(mes_num), int(dia)).date()
                            hora_int = int(hora_str)
                            if hora_int == 0:
                                hora_int = 0
                            hora = time(hora_int, int(minuto_str))
                        except ValueError as e:
                            errores.append(f"Fila {row_num}: Fecha/hora inválida '{horario_str}' - {str(e)}")
                            continue
                    else:
                        # Intentar otros formatos
                        fecha = parse_date(horario_str)
                        hora = parse_time(horario_str)

                        if not fecha or not hora:
                            errores.append(f"Fila {row_num}: Formato de horario inválido '{horario_str}'")
                            continue

                    # Agregar a datos agrupados
                    if fecha and hora:
                        key = (rut_str, fecha)
                        if key not in datos_agrupados:
                            datos_agrupados[key] = []
                        datos_agrupados[key].append(hora)

            except Exception as e:
                errores.append(f"Fila {row_num}: Error procesando fila - {str(e)}")

        # Ahora procesar los datos agrupados
        ruts_encontrados = set()

        for (rut_str, fecha), horas in datos_agrupados.items():
            try:
                # Buscar funcionario por RUT
                funcionario = find_user_by_rut(rut_str)
                if not funcionario:
                    errores.append(f"RUT {rut_str} no encontrado - omitiendo {len(horas)} registros")
                    ruts_no_encontrados_set.add(rut_str)
                    ruts_no_encontrados += len(horas)
                    continue

                ruts_encontrados.add(rut_str)

                # Ordenar las horas del día
                horas_ordenadas = sorted(horas)

                # Determinar entrada y salida basándose en las horas.
                # Bloques del día para distinguir turnos nocturnos de entradas tempranas:
                # - madrugada (0-4h): podría ser salida de turno nocturno previo O entrada muy temprana
                # - mañana (5-11h): entradas diurnas reales (incluye entradas antes de las 7:30)
                # - tarde (12-23h): salidas diurnas
                hora_entrada = None
                hora_salida = None

                horas_madrugada = [h for h in horas_ordenadas if h.hour < 5]
                horas_manana    = [h for h in horas_ordenadas if 5 <= h.hour < 12]
                horas_tarde     = [h for h in horas_ordenadas if h.hour >= 12]

                if horas_manana:
                    # Hay entrada diurna real → tomar la primera (puede ser antes de las 7:30)
                    hora_entrada = horas_manana[0]  # Primera hora de la mañana
                    # Si además hay madrugada, es una salida de turno nocturno previo
                else:
                    # Sin registros de mañana: la madrugada es la entrada real (turno muy temprano)
                    if horas_madrugada:
                        hora_entrada = horas_madrugada[0]

                if horas_tarde:
                    hora_salida = horas_tarde[-1]  # Última hora de la tarde

                # Crear o actualizar registro de asistencia
                registro, created = RegistroAsistencia.objects.get_or_create(
                    funcionario=funcionario,
                    fecha=fecha,
                    defaults={
                        'hora_entrada_real': hora_entrada,
                        'hora_salida_real': hora_salida,
                        'procesado_por': self.request.user,
                    }
                )

                if not created:
                    # Actualizar si ya existe
                    registro.hora_entrada_real = hora_entrada
                    registro.hora_salida_real = hora_salida
                    registro.procesado_por = self.request.user
                    registro.save()

                registros_creados += 1

            except Exception as e:
                errores.append(f"Error procesando {rut_str} fecha {fecha}: {str(e)}")

        # Logging final con resumen detallado
        logger.info(f"Procesamiento completado: {registros_creados} registros creados/actualizados")
        logger.info(f"RUTs únicos en archivo: {len(ruts_unicos_en_archivo)}")
        logger.info(f"RUTs encontrados en BD: {len(ruts_encontrados)} - {sorted(ruts_encontrados) if ruts_encontrados else 'Ninguno'}")
        logger.info(f"RUTs NO encontrados en BD: {len(ruts_no_encontrados_set)} - {sorted(ruts_no_encontrados_set) if ruts_no_encontrados_set else 'Ninguno'}")
        logger.info(f"Total filas con RUTs no encontrados: {ruts_no_encontrados}, otros errores: {len(errores) - ruts_no_encontrados}")
        logger.info("✅ Sistema mejorado: Procesa múltiples marcaciones por día correctamente")

        return registros_creados, errores


class DescargarAsistenciaView(LoginRequiredMixin, View):
    """Vista para descargar registros de asistencia como Excel"""

    def get(self, request):
        # Obtener parámetros de filtro
        usuario_id = request.GET.get('usuario')
        anio = request.GET.get('anio')
        mes = request.GET.get('mes')
        estado = request.GET.get('estado')

        # Filtrar registros
        queryset = RegistroAsistencia.objects.select_related('funcionario', 'horario_asignado')

        if usuario_id:
            queryset = queryset.filter(funcionario_id=usuario_id)
        if anio:
            queryset = queryset.filter(fecha__year=anio)
        if mes:
            queryset = queryset.filter(fecha__month=mes)
        if estado:
            queryset = queryset.filter(estado=estado)

        registros = queryset.order_by('fecha', 'funcionario__last_name')

        # Crear archivo Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Registros de Asistencia"

        # Headers
        headers = [
            'Fecha', 'RUT', 'Nombre Completo', 'Rol',
            'Hora Estipulada', 'Hora Entrada Real', 'Hora Salida Real',
            'Minutos Retraso', 'Minutos Trabajados', 'Estado'
        ]
        for col_num, header in enumerate(headers, 1):
            ws.cell(row=1, column=col_num, value=header)

        # Datos
        for row_num, registro in enumerate(registros, 2):
            ws.cell(row=row_num, column=1, value=registro.fecha.strftime('%Y-%m-%d'))
            ws.cell(row=row_num, column=2, value=registro.funcionario.run)
            ws.cell(row=row_num, column=3, value=registro.funcionario.get_full_name())
            ws.cell(row=row_num, column=4, value=registro.funcionario.get_role_display())

            if registro.horario_asignado:
                ws.cell(row=row_num, column=5, value=registro.horario_asignado.hora_entrada.strftime('%H:%M:%S'))
            else:
                ws.cell(row=row_num, column=5, value='Sin horario')

            if registro.hora_entrada_real:
                ws.cell(row=row_num, column=6, value=registro.hora_entrada_real.strftime('%H:%M:%S'))
            else:
                ws.cell(row=row_num, column=6, value='')

            if registro.hora_salida_real:
                ws.cell(row=row_num, column=7, value=registro.hora_salida_real.strftime('%H:%M:%S'))
            else:
                ws.cell(row=row_num, column=7, value='')

            ws.cell(row=row_num, column=8, value=registro.minutos_retraso)
            ws.cell(row=row_num, column=9, value=registro.minutos_trabajados or '')
            ws.cell(row=row_num, column=10, value=registro.get_estado_display())

        # Crear respuesta HTTP
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        filename = f"registros_asistencia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename={filename}'

        wb.save(response)
        return response


class CrearHorarioView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Vista para crear horario manualmente para un funcionario"""
    model = HorarioFuncionario
    form_class = HorarioFuncionarioForm
    template_name = 'asistencia/crear_horario.html'

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def dispatch(self, request, *args, **kwargs):
        # Verificar si el funcionario ya tiene un horario
        funcionario_id = self.kwargs.get('funcionario_id')
        if funcionario_id:
            existing_horario = HorarioFuncionario.objects.filter(funcionario_id=funcionario_id).first()
            if existing_horario:
                messages.warning(
                    request,
                    f'El funcionario ya tiene un horario asignado. Use la opción "Editar" para modificarlo.'
                )
                return redirect('asistencia:editar_horario', pk=existing_horario.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        funcionario_id = self.kwargs.get('funcionario_id')
        if funcionario_id:
            context['funcionario'] = get_object_or_404(CustomUser, pk=funcionario_id)
        return context

    def form_valid(self, form):
        funcionario_id = self.kwargs.get('funcionario_id')
        if funcionario_id:
            form.instance.funcionario_id = funcionario_id
        messages.success(self.request, f'Horario creado exitosamente para {form.instance.funcionario.get_full_name()}')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('asistencia:gestion_horarios')


class EditarHorarioView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Vista para editar horario de un funcionario"""
    model = HorarioFuncionario
    form_class = HorarioFuncionarioForm
    template_name = 'asistencia/editar_horario.html'

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def form_valid(self, form):
        messages.success(self.request, f'Horario actualizado exitosamente para {form.instance.funcionario.get_full_name()}')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('asistencia:gestion_horarios')


class ToggleHorarioView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para activar/desactivar horario"""

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def post(self, request, pk):
        horario = get_object_or_404(HorarioFuncionario, pk=pk)
        horario.activo = not horario.activo
        horario.save()

        estado = "activado" if horario.activo else "desactivado"
        messages.success(request, f'Horario {estado} exitosamente para {horario.funcionario.get_full_name()}')

        return redirect('asistencia:gestion_horarios')


class DetalleUsuarioAsistenciaView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Vista detallada de asistencia de un usuario específico organizada por año"""
    template_name = 'asistencia/detalle_usuario.html'

    def test_func(self):
        # Solo administradores, secretarias, directores y directivos pueden ver detalles
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtener el usuario
        user_id = self.kwargs.get('user_id')
        usuario = get_object_or_404(CustomUser, pk=user_id)

        # Obtener todos los registros del usuario
        registros_usuario = RegistroAsistencia.objects.filter(
            funcionario=usuario
        ).select_related('horario_asignado', 'procesado_por').order_by('-fecha')

        # Estadísticas generales del usuario
        total_registros = registros_usuario.count()
        registros_puntuales = registros_usuario.filter(estado='PUNTUAL').count()
        registros_retraso = registros_usuario.filter(estado='RETRASO').count()
        registros_ausentes = registros_usuario.filter(estado='AUSENTE').count()
        total_minutos_retraso = sum(r.minutos_retraso for r in registros_usuario if r.minutos_retraso > 0)

        ESTADO_DISPLAY = {
            'DIA_ADMINISTRATIVO': 'Día Administrativo',
            'MEDIO_DIA': 'Medio Día Administrativo',
            'LICENCIA_MEDICA': 'Licencia Médica',
        }

        class RegistroVirtual:
            """Registro virtual para días con permiso/licencia sin marcación"""
            def __init__(self, fecha, estado):
                self.fecha = fecha
                self.estado = estado
                self.minutos_retraso = 0
                self.hora_entrada_real = None
                self.hora_salida_real = None
                self.minutos_trabajados = None
                self.horario_asignado = None
                self.alegacion = None
                self._estado_display = ESTADO_DISPLAY.get(estado, estado)
            @property
            def pk(self):
                return None
            def get_estado_display(self):
                return self._estado_display

        # Consultar permisos y licencias del usuario (una sola vez)
        from permisos.models import SolicitudPermiso
        from licencias.models import LicenciaMedica
        from datetime import timedelta as td

        # Agrupar registros por año
        registros_por_anio = {}
        anios_disponibles = registros_usuario.values_list('fecha__year', flat=True).distinct().order_by('-fecha__year')

        for anio in anios_disponibles:
            registros_anio = registros_usuario.filter(fecha__year=anio).order_by('-fecha')

            # Consultar permisos aprobados para este año
            primer_dia_anio = datetime(anio, 1, 1).date()
            ultimo_dia_anio = datetime(anio, 12, 31).date()

            permisos_qs = SolicitudPermiso.objects.filter(
                usuario=usuario,
                estado='APROBADO',
                fecha_inicio__lte=ultimo_dia_anio
            ).filter(
                Q(fecha_termino__gte=primer_dia_anio) | Q(fecha_termino__isnull=True)
            )

            permisos_por_fecha = {}
            for permiso in permisos_qs:
                inicio = max(permiso.fecha_inicio, primer_dia_anio)
                fin = permiso.fecha_termino or ultimo_dia_anio
                fin = min(fin, ultimo_dia_anio)
                d = inicio
                while d <= fin:
                    permisos_por_fecha[d] = permiso
                    d += td(days=1)

            # Consultar licencias médicas para este año
            licencias_qs = LicenciaMedica.objects.filter(
                usuario=usuario,
                fecha_inicio__lte=ultimo_dia_anio
            )

            licencias_por_fecha = {}
            for licencia in licencias_qs:
                fin_lic = licencia.fecha_inicio + td(days=licencia.dias - 1)
                inicio = max(licencia.fecha_inicio, primer_dia_anio)
                fin = min(fin_lic, ultimo_dia_anio)
                d = inicio
                while d <= fin:
                    licencias_por_fecha[d] = licencia
                    d += td(days=1)

            # Agrupar por mes dentro del año
            registros_por_mes = {}
            meses_con_datos = registros_anio.values_list('fecha__month', flat=True).distinct().order_by('fecha__month')

            total_minutos_retraso_anio = 0
            for mes in meses_con_datos:
                registros_mes_qs = registros_anio.filter(fecha__month=mes).order_by('fecha')
                registros_mes_list = list(registros_mes_qs)
                fechas_con_registro = {r.fecha for r in registros_mes_list}

                # Agregar registros virtuales para días con permiso/licencia sin registro
                primer_dia_mes = datetime(anio, mes, 1).date()
                ultimo_dia_mes = (primer_dia_mes + td(days=32)).replace(day=1) - td(days=1)
                d = primer_dia_mes
                while d <= ultimo_dia_mes:
                    if d not in fechas_con_registro:
                        if d in licencias_por_fecha:
                            registros_mes_list.append(RegistroVirtual(d, 'LICENCIA_MEDICA'))
                        elif d in permisos_por_fecha:
                            permiso = permisos_por_fecha[d]
                            if permiso.dias_solicitados == 0.5:
                                registros_mes_list.append(RegistroVirtual(d, 'MEDIO_DIA'))
                            else:
                                registros_mes_list.append(RegistroVirtual(d, 'DIA_ADMINISTRATIVO'))
                    d += td(days=1)

                registros_mes_list.sort(key=lambda r: r.fecha)

                minutos_retraso_mes = sum(r.minutos_retraso for r in registros_mes_qs if r.minutos_retraso > 0)
                total_minutos_retraso_anio += minutos_retraso_mes

                ausentes_mes = sum(1 for r in registros_mes_list if r.estado == 'AUSENTE')
                admin_mes = sum(1 for r in registros_mes_list if r.estado == 'DIA_ADMINISTRATIVO')
                licencia_mes = sum(1 for r in registros_mes_list if r.estado == 'LICENCIA_MEDICA')
                medio_dia_mes = sum(1 for r in registros_mes_list if r.estado == 'MEDIO_DIA')

                registros_por_mes[mes] = {
                    'registros': registros_mes_list,
                    'total': len(registros_mes_list),
                    'puntuales': sum(1 for r in registros_mes_list if r.estado == 'PUNTUAL'),
                    'retrasos': sum(1 for r in registros_mes_list if r.estado == 'RETRASO'),
                    'ausentes': ausentes_mes,
                    'admin': admin_mes,
                    'licencias': licencia_mes,
                    'medio_dia': medio_dia_mes,
                    'minutos_retraso_mes': minutos_retraso_mes,
                }

            registros_por_anio[anio] = {
                'registros_por_mes': registros_por_mes,
                'total_anio': registros_anio.count(),
                'puntuales_anio': registros_anio.filter(estado='PUNTUAL').count(),
                'minutos_retraso_anio': total_minutos_retraso_anio,
            }

        # Horario asignado
        horario_actual = HorarioFuncionario.objects.filter(
            funcionario=usuario, activo=True
        ).first()

        # Generar horario_semanal
        horario_semanal = []
        es_sereno = usuario.funcion == 'SERENO'
        dias_totales = 7 if es_sereno else 5

        DIA_CHOICES_DICT = {
            0: 'Lunes', 1: 'Martes', 2: 'Miércoles',
            3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'
        }

        dias_configurados = {}
        if horario_actual:
            for dh in horario_actual.dias.all():
                dias_configurados[dh.dia_semana] = dh

        for i in range(dias_totales):
            dia_obj = dias_configurados.get(i)
            if dia_obj:
                horario_semanal.append({
                    'dia_semana': i,
                    'nombre': DIA_CHOICES_DICT[i],
                    'activo': dia_obj.activo,
                    'hora_entrada': dia_obj.hora_entrada.strftime('%H:%M') if dia_obj.hora_entrada else '',
                    'hora_salida': dia_obj.hora_salida.strftime('%H:%M') if dia_obj.hora_salida else ''
                })
            else:
                # Usar valores por defecto si no hay horario configurado para este día
                hora_entrada_default = '07:55'
                if horario_actual and horario_actual.hora_entrada:
                    hora_entrada_default = horario_actual.hora_entrada.strftime('%H:%M')
                horario_semanal.append({
                    'dia_semana': i,
                    'nombre': DIA_CHOICES_DICT[i],
                    'activo': True,
                    'hora_entrada': hora_entrada_default,
                    'hora_salida': '17:00'
                })


        # Meses para referencia
        context['meses'] = [
            (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
            (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
            (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
        ]

        context.update({
            'usuario': usuario,
            'registros_por_anio': registros_por_anio,
            'horario_actual': horario_actual,
            'horario_semanal': horario_semanal,
            'es_sereno': es_sereno,
            'estadisticas_funcionario': {
                'total_registros': total_registros,
                'registros_puntuales': registros_puntuales,
                'registros_retraso': registros_retraso,
                'registros_ausentes': registros_ausentes,
                'total_minutos_retraso': total_minutos_retraso,
                'anios_con_asistencia': len(anios_disponibles),
                'promedio_por_anio': round(total_registros / len(anios_disponibles), 1) if anios_disponibles else 0,
                'porcentaje_puntualidad': round((registros_puntuales / total_registros * 100) if total_registros > 0 else 0, 1),
            }
        })

        return context


class EliminarRegistroAsistenciaView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para eliminar un registro específico de asistencia"""

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

    def post(self, request, pk):
        registro = get_object_or_404(RegistroAsistencia, pk=pk)
        usuario = registro.funcionario
        registro.delete()

        messages.success(request, f'Registro de asistencia del {registro.fecha} eliminado exitosamente para {usuario.get_full_name()}')
        return redirect('asistencia:detalle_usuario', user_id=usuario.id)


class CrearAlegacionView(LoginRequiredMixin, View):
    """Vista para que usuarios creen alegaciones sobre sus registros de asistencia"""

    def post(self, request):
        registro_id = request.POST.get('registro_id')
        motivo = request.POST.get('motivo')
        evidencia = request.FILES.get('evidencia')

        if not registro_id or not motivo:
            messages.error(request, 'Datos incompletos para la alegación')
            return redirect('asistencia:mi_asistencia')

        try:
            registro = RegistroAsistencia.objects.get(
                id=registro_id,
                funcionario=request.user
            )

            # Verificar que el registro permita alegaciones
            if registro.estado not in ['RETRASO', 'AUSENTE']:
                messages.error(request, 'Solo se pueden alegar registros con retraso o ausencia')
                return redirect('asistencia:mi_asistencia')

            # Verificar que no exista ya una alegación
            if hasattr(registro, 'alegacion'):
                messages.error(request, 'Ya existe una alegación para este registro')
                return redirect('asistencia:mi_asistencia')

            # Crear la alegación
            AlegacionAsistencia.objects.create(
                registro_asistencia=registro,
                motivo=motivo,
                evidencia=evidencia
            )

            messages.success(request, 'Alegación enviada correctamente. Será revisada por un administrador.')
            return redirect('asistencia:mi_asistencia')

        except RegistroAsistencia.DoesNotExist:
            messages.error(request, 'Registro no encontrado')
            return redirect('asistencia:mi_asistencia')
        except Exception as e:
            messages.error(request, f'Error al crear la alegación: {str(e)}')
            return redirect('asistencia:mi_asistencia')


class GestionAlegacionesView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Vista para que administradores gestionen alegaciones"""

    model = AlegacionAsistencia
    template_name = 'asistencia/gestion_alegaciones.html'
    context_object_name = 'alegaciones'
    paginate_by = 20

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def get_queryset(self):
        queryset = AlegacionAsistencia.objects.select_related(
            'registro_asistencia__funcionario',
            'revisado_por'
        ).order_by('-fecha_alegacion')

        # Filtros
        estado = self.request.GET.get('estado')
        usuario = self.request.GET.get('usuario')

        if estado:
            queryset = queryset.filter(estado=estado)
        if usuario:
            queryset = queryset.filter(registro_asistencia__funcionario__run__icontains=usuario)

        return queryset


class RevisarAlegacionView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para revisar y responder alegaciones"""

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def post(self, request, pk=0):
        alegacion_id = request.POST.get('alegacion_id')
        if alegacion_id:
            pk = alegacion_id

        alegacion = get_object_or_404(AlegacionAsistencia, pk=pk)

        accion = request.POST.get('accion')
        respuesta = request.POST.get('respuesta', '')

        if accion not in ['aprobar', 'rechazar']:
            messages.error(request, 'Acción no válida')
            return redirect('asistencia:gestion_alegaciones')

        if not respuesta.strip():
            messages.error(request, 'Debe proporcionar una respuesta')
            return redirect('asistencia:gestion_alegaciones')

        # Actualizar alegación
        alegacion.estado = 'APROBADA' if accion == 'aprobar' else 'RECHAZADA'
        alegacion.respuesta_admin = respuesta
        alegacion.revisado_por = request.user
        alegacion.fecha_revision = timezone.now()
        alegacion.save()
        
        registrar_log(
            usuario=request.user,
            tipo='APPROVE' if accion == 'aprobar' else 'RECHAZADA',
            accion='Revisión de Alegación',
            descripcion=f'Se {alegacion.get_estado_display()} la alegación de {alegacion.funcionario.get_full_name()}',
            ip_address=get_client_ip(request)
        )

        # Si se aprueba, cambiar el estado del registro a JUSTIFICADO
        if accion == 'aprobar':
            registro = alegacion.registro_asistencia
            registro.estado = 'JUSTIFICADO'
            registro.justificacion_manual = f'Aprobada alegación: {respuesta}'
            registro.justificado_por = request.user
            registro.fecha_justificacion = timezone.now()
            registro.save()

        estado_texto = 'aprobada' if accion == 'aprobar' else 'rechazada'
        messages.success(request, f'Alegación {estado_texto} correctamente')
        return redirect('asistencia:gestion_alegaciones')


class GestionDiasFestivosView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Vista para gestionar días festivos"""

    model = DiaFestivo
    template_name = 'asistencia/gestion_festivos.html'
    context_object_name = 'dias_festivos'
    paginate_by = 20

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def get_queryset(self):
        return DiaFestivo.objects.order_by('-fecha')


class CrearDiaFestivoView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Vista para crear días festivos"""

    model = DiaFestivo
    form_class = DiaFestivoForm
    template_name = 'asistencia/crear_festivo.html'
    success_url = reverse_lazy('asistencia:gestion_festivos')

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        messages.success(self.request, f'Día festivo "{form.instance.nombre}" creado correctamente')
        return super().form_valid(form)


class EliminarDiaFestivoView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para eliminar días festivos"""

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def post(self, request, pk):
        festivo = get_object_or_404(DiaFestivo, pk=pk)
        nombre = festivo.nombre
        festivo.delete()

        messages.success(request, f'Día festivo "{nombre}" eliminado correctamente')
        return redirect('asistencia:gestion_festivos')


class JustificarRegistroView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para justificar manualmente registros de asistencia"""

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def post(self, request, pk):
        registro = get_object_or_404(RegistroAsistencia, pk=pk)
        justificacion = request.POST.get('justificacion', '').strip()

        if not justificacion:
            messages.error(request, 'Debe proporcionar una justificación')
            return redirect('asistencia:detalle_usuario', user_id=registro.funcionario.id)

        # Justificar el registro
        registro.estado = 'JUSTIFICADO'
        registro.justificacion_manual = justificacion
        registro.justificado_por = request.user
        registro.fecha_justificacion = timezone.now()
        registro.save()

        messages.success(request, f'Registro justificado correctamente')
        return redirect('asistencia:detalle_usuario', user_id=registro.funcionario.id)


class EditarRegistroAsistenciaView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para editar manualmente las horas de entrada/salida de un registro de asistencia (justificar)"""

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def get(self, request, pk):
        registro = get_object_or_404(RegistroAsistencia, pk=pk)
        form = EditarRegistroAsistenciaForm()
        context = {
            'registro': registro,
            'form': form,
        }
        return render(request, 'asistencia/editar_registro_asistencia.html', context)

    def post(self, request, pk):
        registro = get_object_or_404(RegistroAsistencia, pk=pk)
        form = EditarRegistroAsistenciaForm(request.POST)

        if form.is_valid():
            hora_entrada = form.cleaned_data.get('hora_entrada_real')
            hora_salida = form.cleaned_data.get('hora_salida_real')
            justificacion = form.cleaned_data.get('justificacion_manual', '').strip()

            # Actualizar horas si se proporcionaron
            if hora_entrada:
                registro.hora_entrada_real = hora_entrada
            if hora_salida:
                registro.hora_salida_real = hora_salida

            # Actualizar justificación manual
            if justificacion:
                registro.justificacion_manual = justificacion
                registro.justificado_por = request.user
                registro.fecha_justificacion = timezone.now()

            # Recalcular el estado automáticamente
            registro.save()

            messages.success(request, f'Registro actualizado correctamente para {registro.funcionario.get_full_name()}')
            return redirect('asistencia:detalle_usuario', user_id=registro.funcionario.id)
        else:
            # Mostrar el formulario con errores
            context = {
                'registro': registro,
                'form': form,
            }
            return render(request, 'asistencia/editar_registro_asistencia.html', context)


class EliminarTodosRegistrosUsuarioView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para eliminar todos los registros de asistencia de un usuario"""

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

    def post(self, request, user_id):
        usuario = get_object_or_404(CustomUser, pk=user_id)

        # Contar registros antes de eliminar
        count = RegistroAsistencia.objects.filter(funcionario=usuario).count()

        # Eliminar todos los registros
        RegistroAsistencia.objects.filter(funcionario=usuario).delete()

        messages.success(request, f'Se eliminaron {count} registros de asistencia para {usuario.get_full_name()}')
        return redirect('asistencia:detalle_usuario', user_id=usuario.id)


class EliminarTodasAsistenciasView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para eliminar TODOS los registros de asistencia de todos los funcionarios"""

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

    def post(self, request):
        # Verificar confirmación doble
        confirmacion = request.POST.get('confirmacion')
        if confirmacion != 'ELIMINAR_TODO':
            messages.error(request, 'Confirmación incorrecta. No se realizó la eliminación.')
            return redirect('asistencia:gestion_asistencia')

        # Contar registros antes de eliminar
        total_registros = RegistroAsistencia.objects.count()
        total_funcionarios = RegistroAsistencia.objects.values('funcionario').distinct().count()

        # Eliminar todos los registros
        RegistroAsistencia.objects.all().delete()

        messages.success(
            request,
            f'Se eliminaron {total_registros} registros de asistencia de {total_funcionarios} funcionarios.'
        )
        return redirect('asistencia:gestion_asistencia')


class ReporteAsistenciaMensualView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para generar reporte mensual de asistencia en PDF (solo para roles autorizados)"""

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def get(self, request, anio=None, mes=None):
        import calendar as cal
        # Si no se pasan como parámetros de URL, obtener de GET
        if not anio or not mes or anio == '0':
            anio_str = request.GET.get('anio')
            mes_str = request.GET.get('mes')

            if anio_str and mes_str:
                try:
                    anio = int(anio_str)
                    mes = int(mes_str)
                except ValueError:
                    from django.contrib import messages
                    messages.error(request, 'Los valores de mes y año deben ser números válidos.')
                    return redirect(reverse('asistencia:gestion_asistencia'))
            else:
                from django.contrib import messages
                messages.error(request, 'Debe seleccionar mes y año para generar el reporte.')
                return redirect(reverse('asistencia:gestion_asistencia'))
        # Obtener todos los funcionarios que deben tener asistencia
        from users.models import CustomUser
        todos_funcionarios = CustomUser.objects.filter(
            role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA', 'ADMIN']
        ).order_by('last_name', 'first_name')

        # Obtener datos del mes
        registros_mes = RegistroAsistencia.objects.filter(
            fecha__year=anio,
            fecha__month=mes
        ).select_related('funcionario', 'horario_asignado')

        # Crear mapa de registros por funcionario
        registros_por_funcionario = {}
        for registro in registros_mes:
            func_id = registro.funcionario.id
            if func_id not in registros_por_funcionario:
                registros_por_funcionario[func_id] = []
            registros_por_funcionario[func_id].append(registro)

        # Procesar cada funcionario y solo incluir aquellos con atrasos o inasistencias
        funcionarios_lista = []
        for funcionario in todos_funcionarios:
            func_id = funcionario.id
            registros_funcionario = registros_por_funcionario.get(func_id, [])

            # Inicializar datos del funcionario
            func_data = {
                'funcionario': funcionario,
                'atrasos': [],
                'inasistencias': [],
                'justificados': [],
                'tiene_registros': len(registros_funcionario) > 0,
                'total_atrasos': 0,
                'total_minutos_retraso': 0,
                'total_inasistencias_sin_justificar': 0,
            }

            # Procesar registros del funcionario
            for registro in registros_funcionario:
                if registro.estado == 'RETRASO':
                    atraso_info = {
                        'fecha': registro.fecha,
                        'hora_entrada': registro.hora_entrada_real,
                        'minutos_retraso': registro.minutos_retraso,
                    }
                    func_data['atrasos'].append(atraso_info)
                    func_data['total_atrasos'] += 1
                    func_data['total_minutos_retraso'] += registro.minutos_retraso or 0
                elif registro.estado == 'AUSENTE':
                    # Ignorar si es antes de su ingreso
                    if registro.fecha < funcionario.date_joined.date():
                        continue
                        
                    inasistencia_info = {
                        'fecha': registro.fecha,
                        'hora_esperada': registro.horario_asignado.hora_entrada if registro.horario_asignado else None,
                        'justificada': False,
                    }
                    func_data['inasistencias'].append(inasistencia_info)
                    func_data['total_inasistencias_sin_justificar'] += 1
                elif registro.estado in ('JUSTIFICADO', 'DIA_ADMINISTRATIVO', 'LICENCIA_MEDICA'):
                    if registro.estado == 'DIA_ADMINISTRATIVO':
                        tipo_just = 'dia_administrativo'
                        detalle = 'Día administrativo aprobado'
                    elif registro.estado == 'LICENCIA_MEDICA':
                        tipo_just = 'licencia'
                        detalle = 'Licencia médica'
                    else:
                        tipo_just = 'permiso' if registro.tiene_permiso_aprobado() else 'licencia' if registro.tiene_licencia_medica() else 'otro'
                        detalle = 'Ausencia justificada'
                    justificado_info = {
                        'fecha': registro.fecha,
                        'tipo': tipo_just,
                        'detalle': detalle,
                    }
                    func_data['justificados'].append(justificado_info)

            # Detectar días sin registro que son inasistencias
            fechas_con_registro = {r.fecha for r in registros_funcionario}
            today = datetime.now().date()
            num_dias = cal.monthrange(anio, mes)[0]
            for dia in range(1, num_dias + 1):
                fecha = datetime(anio, mes, dia).date()
                if fecha >= today:
                    continue
                if fecha in fechas_con_registro:
                    continue
                if DiaFestivo.objects.filter(fecha=fecha).exists():
                    continue
                if fecha.weekday() >= 5 and not (funcionario.funcion == 'SERENO' or funcionario.tipo_funcionario == 'SERENO'):
                    continue
                if fecha < funcionario.date_joined.date():
                    continue
                inasistencia_info = {
                    'fecha': fecha,
                    'hora_esperada': None,
                    'justificada': False,
                }
                func_data['inasistencias'].append(inasistencia_info)
                func_data['total_inasistencias_sin_justificar'] += 1

            # Solo incluir funcionarios que tienen atrasos, inasistencias o justificaciones
            if func_data['atrasos'] or func_data['inasistencias'] or func_data['justificados']:
                # Ordenar todas las listas por fecha
                func_data['atrasos'].sort(key=lambda x: x['fecha'])
                func_data['inasistencias'].sort(key=lambda x: x['fecha'])
                func_data['justificados'].sort(key=lambda x: x['fecha'])
                funcionarios_lista.append(func_data)

        # Nombre del mes
        meses = [
            'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        ]
        nombre_mes = meses[mes - 1]

        # Renderizar template HTML para PDF
        html_content = render_to_string('asistencia/reporte_mensual_pdf.html', {
            'funcionarios': funcionarios_lista,
            'anio': anio,
            'mes': mes,
            'nombre_mes': nombre_mes,
            'fecha_actual': datetime.now(),
        })

        # Generar PDF
        pdf_file = HTML(string=html_content).write_pdf()

        # Crear respuesta HTTP
        response = HttpResponse(pdf_file, content_type='application/pdf')
        filename = f'reporte_asistencia_{anio}_{mes:02d}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response


class RecalcularEstadoAsistenciaView(LoginRequiredMixin, View):
    """Vista para recalcular el estado de todos los registros de asistencia del usuario actual"""

    def post(self, request):
        # Obtener todos los registros del usuario
        registros = RegistroAsistencia.objects.filter(funcionario=request.user)

        if not registros.exists():
            messages.warning(request, 'No tiene registros de asistencia para recalcular.')
            return redirect('asistencia:mi_asistencia')

        registros_actualizados = 0

        # Recalcular estado para cada registro
        for registro in registros:
            # Actualizar horario_asignado al horario actual del usuario (si existe)
            try:
                horario_actual = HorarioFuncionario.objects.filter(
                    funcionario=registro.funcionario, activo=True
                ).first()
                if horario_actual:
                    registro.horario_asignado = horario_actual
            except:
                pass

            # Forzar recálculo del estado llamando al método save
            registro.save()

            registros_actualizados += 1

        messages.success(
            request,
            f'Se recalcularon {registros_actualizados} registros de asistencia. Los estados ahora reflejan su horario actual y permisos/licencias vigentes.'
        )

        # Redirigir de vuelta a la vista de asistencia con los filtros actuales
        mes = request.GET.get('mes')
        anio = request.GET.get('anio')

        if mes and anio:
            return redirect(f'/asistencia/mi-asistencia/?mes={mes}&anio={anio}')
        else:
            return redirect('asistencia:mi_asistencia')


class RecalcularTodaAsistenciaView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para recalcular TODOS los registros de asistencia de TODOS los funcionarios"""

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def post(self, request):
        registros = RegistroAsistencia.objects.select_related('funcionario').all()

        if not registros.exists():
            messages.warning(request, 'No hay registros de asistencia para recalcular.')
            return redirect('asistencia:gestion_asistencia')

        registros_actualizados = 0

        for registro in registros:
            try:
                horario_actual = HorarioFuncionario.objects.filter(
                    funcionario=registro.funcionario, activo=True
                ).first()
                if horario_actual:
                    registro.horario_asignado = horario_actual
            except Exception:
                pass

            registro.save()
            registros_actualizados += 1

        messages.success(
            request,
            f'Se recalcularon {registros_actualizados} registros de asistencia de todos los funcionarios.'
        )

        registrar_log(
            usuario=request.user,
            tipo='UPDATE',
           accion='Recálculo Masivo de Asistencia',
            descripcion=f'Se recalcularon {registros_actualizados} registros de asistencia',
            ip_address=get_client_ip(request)
        )

        return redirect('asistencia:gestion_asistencia')


class RecalcularAsistenciaUsuarioView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para recalcular la asistencia de un usuario en particular"""

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def post(self, request, user_id):
        usuario = get_object_or_404(CustomUser, id=user_id)
        mes = request.POST.get('mes')
        anio = request.POST.get('anio')

        registros = RegistroAsistencia.objects.filter(funcionario=usuario)

        if mes and anio:
            try:
                mes = int(mes)
                anio = int(anio)
                registros = registros.filter(fecha__month=mes, fecha__year=anio)
            except ValueError:
                pass

        if not registros.exists():
            messages.warning(request, f'No hay registros de asistencia para {usuario.get_full_name()} en ese periodo.')
            return redirect(f'/asistencia/usuario/{user_id}/')

        registros_actualizados = 0

        for registro in registros:
            try:
                horario_actual = HorarioFuncionario.objects.filter(
                    funcionario=registro.funcionario, activo=True
                ).first()
                if horario_actual:
                    registro.horario_asignado = horario_actual
            except Exception:
                pass

            registro.save()
            registros_actualizados += 1

        # Formatear mes y anio para el redirect y el log si existen
        texto_periodo = ""
        url_redirect = f'/asistencia/usuario/{user_id}/'
        
        if mes and anio:
            texto_periodo = f" (Mes {mes}/{anio})"
            url_redirect += f"?anio={anio}"

        messages.success(
            request,
            f'Se recalcularon {registros_actualizados} registros de asistencia para {usuario.get_full_name()}{texto_periodo}.'
        )

        registrar_log(
            usuario=request.user,
            tipo='UPDATE',
            accion='Recálculo de Asistencia Individual',
            descripcion=f'Se recalcularon {registros_actualizados} registros para el usuario {usuario.run}{texto_periodo}',
            ip_address=get_client_ip(request)
        )

        return redirect(url_redirect)


class ReporteAsistenciaIndividualView(LoginRequiredMixin, View):
    """Vista para generar reporte individual de asistencia en PDF"""

    def get(self, request, anio, mes):
        import calendar as cal

        # Obtener datos del usuario actual para el mes
        registros_mes = list(RegistroAsistencia.objects.filter(
            funcionario=request.user,
            fecha__year=anio,
            fecha__month=mes
        ).select_related('horario_asignado').order_by('fecha'))

        # Obtener horario del funcionario
        try:
            horario = HorarioFuncionario.objects.get(funcionario=request.user, activo=True)
        except HorarioFuncionario.DoesNotExist:
            horario = None

        # Obtener festivos del mes
        festivos = set(
            DiaFestivo.objects.filter(
                fecha__year=anio, fecha__month=mes
            ).values_list('fecha', flat=True)
        )

        # Determinar si es sereno
        es_sereno = request.user.role == 'FUNCIONARIO' and request.user.funcion == 'SERENO'
        if request.user.tipo_funcionario == 'SERENO':
            es_sereno = True

        # Recopilar detalles de atrasos, inasistencias y justificaciones
        atrasos_detalle = []
        inasistencias_detalle = []
        justificaciones_detalle = []

        # Obtener fechas con registro de forma confiable
        fechas_con_registro = set()
        for r in registros_mes:
            fechas_con_registro.add(r.fecha)

        # Primero: procesar registros existentes por estado
        for registro in registros_mes:
            if registro.estado == 'RETRASO':
                atrasos_detalle.append({
                    'fecha': registro.fecha,
                    'hora_entrada': registro.hora_entrada_real,
                    'minutos_retraso': registro.minutos_retraso,
                })
            elif registro.estado == 'AUSENTE':
                # Ignorar si es antes de su ingreso
                if registro.fecha < request.user.date_joined.date():
                    continue
                    
                inasistencias_detalle.append({
                    'fecha': registro.fecha,
                    'hora_esperada': registro.horario_asignado.hora_entrada if registro.horario_asignado else None,
                })
            elif registro.estado in ['JUSTIFICADO', 'DIA_ADMINISTRATIVO', 'LICENCIA_MEDICA']:
                if registro.estado == 'DIA_ADMINISTRATIVO':
                    tipo = 'permiso'
                elif registro.estado == 'LICENCIA_MEDICA':
                    tipo = 'licencia'
                else:
                    tipo = 'permiso' if registro.tiene_permiso_aprobado() else 'licencia' if registro.tiene_licencia_medica() else 'otro'
                justificaciones_detalle.append({
                    'fecha': registro.fecha,
                    'tipo': tipo,
                })

        # Segundo: detectar días sin registro que son inasistencias
        # Días pasados sin registro, que no sean festivos ni fines de semana (para no serenos)
        today = datetime.now().date()
        num_dias = cal.monthrange(anio, mes)[0]
        ano_escolar_activo = AnoEscolar.get_activo()
        for dia in range(1, num_dias + 1):
            fecha = datetime(anio, mes, dia).date()
            es_pasado = fecha < today
            if not es_pasado:
                continue
            tiene_registro = fecha in fechas_con_registro
            if tiene_registro:
                continue
            es_festivo = fecha in festivos
            if es_festivo:
                continue
            # Verificar año escolar SOLO si hay uno activo configurado
            if ano_escolar_activo and not AnoEscolar.es_dia_escolar(fecha):
                continue
            # Mismo filtro de fin de semana que la página
            dia_semana = fecha.weekday()
            es_fin_de_semana = dia_semana >= 5
            if es_fin_de_semana and not es_sereno:
                continue
            
            # No contar inasistencia si es antes de su ingreso
            if fecha < request.user.date_joined.date():
                continue

            # Verificar si tiene permiso administrativo aprobado
            if SolicitudPermiso.objects.filter(
                usuario=request.user,
                estado='APROBADO',
                fecha_inicio__lte=fecha,
                fecha_termino__gte=fecha
            ).exists():
                justificaciones_detalle.append({'fecha': fecha, 'tipo': 'permiso'})
                continue

            # Verificar si tiene licencia médica
            licencia_cubre = False
            for lic in LicenciaMedica.objects.filter(usuario=request.user, fecha_inicio__lte=fecha):
                fecha_fin_lic = lic.fecha_inicio + timedelta(days=lic.dias - 1)
                if fecha <= fecha_fin_lic:
                    licencia_cubre = True
                    break
            if licencia_cubre:
                justificaciones_detalle.append({'fecha': fecha, 'tipo': 'licencia'})
                continue

            # Es una inasistencia sin registro
            inasistencias_detalle.append({
                'fecha': fecha,
                'hora_esperada': horario.hora_entrada if horario else None,
            })

        # Ordenar por fecha
        atrasos_detalle.sort(key=lambda x: x['fecha'])
        inasistencias_detalle.sort(key=lambda x: x['fecha'])
        justificaciones_detalle.sort(key=lambda x: x['fecha'])

        # Totales
        total_atrasos = len(atrasos_detalle)
        total_inasistencias = len(inasistencias_detalle)
        total_justificados = len(justificaciones_detalle)
        total_minutos_retraso = sum(a['minutos_retraso'] for a in atrasos_detalle)

        # Nombre del mes
        meses = [
            'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        ]
        nombre_mes = meses[mes - 1]

        # Renderizar template HTML para PDF
        html_content = render_to_string('asistencia/reporte_individual_pdf.html', {
            'funcionario': request.user,
            'anio': anio,
            'mes': mes,
            'nombre_mes': nombre_mes,
            'atrasos_detalle': atrasos_detalle,
            'inasistencias_detalle': inasistencias_detalle,
            'justificaciones_detalle': justificaciones_detalle,
            'total_atrasos': total_atrasos,
            'total_inasistencias': total_inasistencias,
            'total_justificados': total_justificados,
            'total_minutos_retraso': total_minutos_retraso,
            'fecha_actual': datetime.now(),
            'ano_escolar': ano_escolar_activo,
        })

        # Generar PDF
        pdf_file = HTML(string=html_content).write_pdf()

        # Crear respuesta HTTP
        response = HttpResponse(pdf_file, content_type='application/pdf')
        filename = f'mi_asistencia_{anio}_{mes:02d}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response


class ExportarRetrasosExcelView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Exporta atrasos a Excel - individual (con user_id) o masivo (sin user_id)"""

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def get(self, request, user_id=None):
        anio = int(request.GET.get('anio', datetime.now().year))
        mes = int(request.GET.get('mes', datetime.now().month))

        wb = openpyxl.Workbook()

        if user_id:
            usuario = get_object_or_404(CustomUser, id=user_id)
            filename = f'atrasos_{usuario.last_name}_{anio}_{mes:02d}.xlsx'

            ws = wb.active
            ws.title = 'Atrasos'
            headers = ['RUT', 'Nombre', 'Fecha', 'Horario Est.', 'Entrada Real', 'Min. Retraso', 'Observación']
            header_fill = openpyxl.styles.PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
            header_font = openpyxl.styles.Font(color='FFFFFF', bold=True, size=10)

            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.fill = header_fill
                cell.font = header_font

            registros = RegistroAsistencia.objects.filter(
                funcionario=usuario,
                fecha__year=anio,
                fecha__month=mes,
                estado='RETRASO'
            ).order_by('fecha')

            row = 2
            for reg in registros:
                ws.cell(row=row, column=1, value=usuario.run)
                ws.cell(row=row, column=2, value=usuario.get_full_name())
                ws.cell(row=row, column=3, value=reg.fecha.strftime('%d/%m/%Y'))
                ws.cell(row=row, column=4, value=reg.horario_asignado.hora_entrada.strftime('%H:%M') if reg.horario_asignado else '-')
                ws.cell(row=row, column=5, value=reg.hora_entrada_real.strftime('%H:%M') if reg.hora_entrada_real else '-')
                ws.cell(row=row, column=6, value=reg.minutos_retraso)
                ws.cell(row=row, column=7, value=reg.justificacion_manual or '')
                row += 1

            # Resumen
            row += 1
            ws.cell(row=row, column=1, value='TOTAL ATRASOS:').font = openpyxl.styles.Font(bold=True)
            ws.cell(row=row, column=2, value=registros.count()).font = openpyxl.styles.Font(bold=True, color='FF0000')
            total_min = sum(r.minutos_retraso for r in registros)
            ws.cell(row=row, column=4, value='TOTAL MIN.').font = openpyxl.styles.Font(bold=True)
            ws.cell(row=row, column=5, value=total_min).font = openpyxl.styles.Font(bold=True, color='FF0000')

            for col in ws.columns:
                max_length = max(len(str(cell.value or '')) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_length + 3, 30)

        else:
            # Masivo: resumen por usuario
            filename = f'atrasos_todos_{anio}_{mes:02d}.xlsx'
            ws = wb.active
            ws.title = 'Resumen Atrasos'

            usuarios = CustomUser.objects.filter(
                registros_asistencia__fecha__year=anio,
                registros_asistencia__fecha__month=mes,
                registros_asistencia__estado='RETRASO'
            ).distinct().order_by('first_name', 'last_name')

            headers = ['N°', 'RUT', 'Nombre', 'Cargo', 'Días con Atraso', 'Total Min. Retraso']
            header_fill = openpyxl.styles.PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
            header_font = openpyxl.styles.Font(color='FFFFFF', bold=True, size=10)

            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.fill = header_fill
                cell.font = header_font

            row = 2
            num = 0
            total_general_min = 0
            for usuario in usuarios:
                registros = RegistroAsistencia.objects.filter(
                    funcionario=usuario,
                    fecha__year=anio,
                    fecha__month=mes,
                    estado='RETRASO'
                )
                dias_atraso = registros.count()
                total_min = sum(r.minutos_retraso for r in registros)
                total_general_min += total_min
                num += 1

                ws.cell(row=row, column=1, value=num)
                ws.cell(row=row, column=2, value=usuario.run)
                ws.cell(row=row, column=3, value=usuario.get_full_name())
                ws.cell(row=row, column=4, value=usuario.get_funcion_display() or usuario.get_role_display())
                ws.cell(row=row, column=5, value=dias_atraso)
                ws.cell(row=row, column=6, value=total_min)

                if total_min >= 60:
                    ws.cell(row=row, column=6).font = openpyxl.styles.Font(color='FF0000', bold=True)

                row += 1

            # Resumen
            row += 1
            ws.cell(row=row, column=4, value='TOTAL GENERAL:').font = openpyxl.styles.Font(bold=True)
            ws.cell(row=row, column=6, value=total_general_min).font = openpyxl.styles.Font(bold=True, color='FF0000', size=12)

            # Ajustar anchos
            ws.column_dimensions['A'].width = 5
            ws.column_dimensions['B'].width = 14
            ws.column_dimensions['C'].width = 30
            ws.column_dimensions['D'].width = 20
            ws.column_dimensions['E'].width = 16
            ws.column_dimensions['F'].width = 18

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response


class ExportarRetrasosPDFView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Exporta atrasos a PDF - individual (con user_id) o masivo (sin user_id)"""

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def get(self, request, user_id=None):
        anio = int(request.GET.get('anio', datetime.now().year))
        mes = int(request.GET.get('mes', datetime.now().month))

        meses = [
            'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        ]
        nombre_mes = meses[mes - 1]

        if user_id:
            usuario = get_object_or_404(CustomUser, id=user_id)
            registros = RegistroAsistencia.objects.filter(
                funcionario=usuario,
                fecha__year=anio,
                fecha__month=mes,
                estado='RETRASO'
            ).order_by('fecha')
            usuarios_data = [{'usuario': usuario, 'registros': registros, 'total': registros.count()}]
            filename = f'atrasos_{usuario.last_name}_{anio}_{mes:02d}.pdf'
            titulo = f'Reporte de Atrasos - {usuario.get_full_name()}'
            template = 'asistencia/reporte_retrasos_pdf.html'
        else:
            usuarios = CustomUser.objects.filter(
                registros_asistencia__fecha__year=anio,
                registros_asistencia__fecha__month=mes,
                registros_asistencia__estado='RETRASO'
            ).distinct().order_by('first_name', 'last_name')

            usuarios_data = []
            total_general = 0
            for usuario in usuarios:
                regs = RegistroAsistencia.objects.filter(
                    funcionario=usuario,
                    fecha__year=anio,
                    fecha__month=mes,
                    estado='RETRASO'
                )
                total_min = sum(r.minutos_retraso for r in regs)
                total_general += total_min
                usuarios_data.append({
                    'usuario': usuario,
                    'dias_atraso': regs.count(),
                    'total_minutos': total_min,
                })

            filename = f'atrasos_todos_{anio}_{mes:02d}.pdf'
            titulo = 'Reporte Masivo de Atrasos'
            template = 'asistencia/reporte_retrasos_masivo_pdf.html'

        html_content = render_to_string(template, {
            'usuarios_data': usuarios_data,
            'total_general': total_general if not user_id else None,
            'anio': anio,
            'mes': mes,
            'nombre_mes': nombre_mes,
            'titulo': titulo,
            'fecha_actual': datetime.now(),
        })

        pdf_file = HTML(string=html_content).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class GestionAnoEscolarView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Vista para gestionar la configuración del año escolar"""
    template_name = 'asistencia/gestion_ano_escolar.html'

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ano_activo'] = AnoEscolar.get_activo()
        context['todos_anos'] = AnoEscolar.objects.all()
        return context

    def post(self, request):
        from django.core.exceptions import ValidationError

        ano = request.POST.get('ano')
        sem1_inicio = request.POST.get('sem1_inicio')
        sem1_fin = request.POST.get('sem1_fin')
        sem2_inicio = request.POST.get('sem2_inicio')
        sem2_fin = request.POST.get('sem2_fin')
        accion = request.POST.get('accion')

        if accion == 'eliminar':
            pk = request.POST.get('pk')
            try:
                ano_obj = AnoEscolar.objects.get(pk=pk)
                ano_obj.delete()
                messages.success(request, f'Año escolar {pk} eliminado correctamente.')
            except AnoEscolar.DoesNotExist:
                messages.error(request, 'Año escolar no encontrado.')
            return redirect('asistencia:gestion_ano_escolar')

        if accion == 'activar':
            pk = request.POST.get('pk')
            try:
                AnoEscolar.objects.update(activo=False)
                ano_obj = AnoEscolar.objects.get(pk=pk)
                ano_obj.activo = True
                ano_obj.save()
                messages.success(request, f'Año escolar {ano_obj.ano} activado correctamente.')
            except AnoEscolar.DoesNotExist:
                messages.error(request, 'Año escolar no encontrado.')
            return redirect('asistencia:gestion_ano_escolar')

        if accion == 'desactivar':
            pk = request.POST.get('pk')
            try:
                ano_obj = AnoEscolar.objects.get(pk=pk)
                ano_obj.activo = False
                ano_obj.save()
                messages.success(request, f'Año escolar {ano_obj.ano} desactivado.')
            except AnoEscolar.DoesNotExist:
                messages.error(request, 'Año escolar no encontrado.')
            return redirect('asistencia:gestion_ano_escolar')

        # Crear o actualizar año escolar
        if not all([ano, sem1_inicio, sem1_fin, sem2_inicio, sem2_fin]):
            messages.error(request, 'Todos los campos son obligatorios.')
            return redirect('asistencia:gestion_ano_escolar')

        try:
            ano = int(ano)
            sem1_inicio = datetime.strptime(sem1_inicio, '%Y-%m-%d').date()
            sem1_fin = datetime.strptime(sem1_fin, '%Y-%m-%d').date()
            sem2_inicio = datetime.strptime(sem2_inicio, '%Y-%m-%d').date()
            sem2_fin = datetime.strptime(sem2_fin, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Formato de fecha inválido.')
            return redirect('asistencia:gestion_ano_escolar')

        # Verificar si ya existe
        existente = AnoEscolar.objects.filter(ano=ano).first()
        if existente:
            existente.sem1_inicio = sem1_inicio
            existente.sem1_fin = sem1_fin
            existente.sem2_inicio = sem2_inicio
            existente.sem2_fin = sem2_fin
            existente.save()
            messages.success(request, f'Año escolar {ano} actualizado correctamente.')
        else:
            AnoEscolar.objects.create(
                ano=ano,
                sem1_inicio=sem1_inicio,
                sem1_fin=sem1_fin,
                sem2_inicio=sem2_inicio,
                sem2_fin=sem2_fin,
                activo=False,
                creado_por=request.user,
            )
            messages.success(request, f'Año escolar {ano} creado correctamente.')

        return redirect('asistencia:gestion_ano_escolar')

class GuardarHorarioSemanalView(LoginRequiredMixin, UserPassesTestMixin, View):
    """API para guardar la configuración del horario semanal de un usuario"""

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def post(self, request, user_id):
        import json
        from django.http import JsonResponse
        from django.db import transaction

        try:
            usuario = get_object_or_404(CustomUser, pk=user_id)
            data = json.loads(request.body)
            
            with transaction.atomic():
                # Obtener o crear el HorarioFuncionario base
                horario_base, created = HorarioFuncionario.objects.get_or_create(
                    funcionario=usuario,
                    defaults={
                        'hora_entrada': time(7, 55),
                        'activo': True
                    }
                )

                dias_data = data.get('dias', [])
                for dia_data in dias_data:
                    dia_semana = int(dia_data.get('dia_semana'))
                    activo = bool(dia_data.get('activo', False))
                    hora_entrada_str = dia_data.get('hora_entrada')
                    hora_salida_str = dia_data.get('hora_salida')

                    hora_entrada = None
                    hora_salida = None

                    if activo:
                        if hora_entrada_str:
                            try:
                                h, m = map(int, hora_entrada_str.split(':'))
                                hora_entrada = time(h, m)
                            except ValueError:
                                pass
                        
                        if hora_salida_str:
                            try:
                                h, m = map(int, hora_salida_str.split(':'))
                                hora_salida = time(h, m)
                            except ValueError:
                                pass
                        
                    # Validar tope de 44 horas semanales antes de guardar
                    if data.get('total_minutos', 0) > 44 * 60:
                         return JsonResponse({
                             'status': 'error', 
                             'message': 'No se puede exceder el límite de 44 horas semanales.'
                         }, status=400)

                    DiaHorario.objects.update_or_create(
                        horario=horario_base,
                        dia_semana=dia_semana,
                        defaults={
                            'activo': activo,
                            'hora_entrada': hora_entrada,
                            'hora_salida': hora_salida
                        }
                    )
                
                # Recalcular todos los registros de asistencia para este usuario
                # Esto permite que la vista 'mi_asistencia' refleje instantáneamente el nuevo horario
                for registro in RegistroAsistencia.objects.filter(funcionario=usuario):
                    registro.save()

            return JsonResponse({'status': 'success', 'message': 'Horario semanal guardado correctamente.'})
            
        except Exception as e:
            logger.error(f"Error guardando horario semanal para {user_id}: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class GestionHorariosExcepcionalesView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Vista para gestionar horarios excepcionales globales del establecimiento"""
    template_name = 'asistencia/gestion_excepcionales.html'

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['excepcionales'] = HorarioExcepcional.objects.select_related('creado_por').all()
        context['form'] = HorarioExcepcionalForm()
        return context


class CrearHorarioExcepcionalView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para crear un horario excepcional y recalcular los registros del día afectado"""

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def post(self, request):
        form = HorarioExcepcionalForm(request.POST)
        if form.is_valid():
            excepcional = form.save(commit=False)
            excepcional.creado_por = request.user
            excepcional.save()

            # Recalcular todos los registros de ese día específico
            registros_del_dia = RegistroAsistencia.objects.filter(fecha=excepcional.fecha)
            count = 0
            for registro in registros_del_dia:
                registro.save()
                count += 1

            registrar_log(
                usuario=request.user,
                tipo='CREATE',
                accion='Creación de Horario Excepcional',
                descripcion=f'Se creó horario excepcional para {excepcional.fecha}: {excepcional.motivo}. '
                            f'Se recalcularon {count} registros.',
                ip_address=get_client_ip(request)
            )

            messages.success(
                request,
                f'Horario excepcional creado para el {excepcional.fecha.strftime("%d/%m/%Y")}. '
                f'Se recalcularon {count} registros de asistencia.'
            )
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')

        return redirect('asistencia:gestion_excepcionales')


class EliminarHorarioExcepcionalView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para eliminar un horario excepcional y recalcular los registros del día afectado"""

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def post(self, request, pk):
        excepcional = get_object_or_404(HorarioExcepcional, pk=pk)
        fecha = excepcional.fecha
        motivo = excepcional.motivo
        excepcional.delete()

        # Recalcular registros del día ahora que ya no hay excepción
        registros_del_dia = RegistroAsistencia.objects.filter(fecha=fecha)
        count = 0
        for registro in registros_del_dia:
            registro.save()
            count += 1

        registrar_log(
            usuario=request.user,
            tipo='DELETE',
            accion='Eliminación de Horario Excepcional',
            descripcion=f'Se eliminó horario excepcional para {fecha}: {motivo}. '
                        f'Se recalcularon {count} registros.',
            ip_address=get_client_ip(request)
        )

        messages.success(
            request,
            f'Horario excepcional del {fecha.strftime("%d/%m/%Y")} eliminado. '
            f'Se recalcularon {count} registros de asistencia.'
        )
        return redirect('asistencia:gestion_excepcionales')

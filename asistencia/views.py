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
from .models import HorarioFuncionario, RegistroAsistencia, DiaFestivo, AlegacionAsistencia
from .forms import CargaHorariosForm, HorarioFuncionarioForm, CargaRegistrosAsistenciaForm
from django.shortcuts import get_object_or_404, redirect
from users.models import CustomUser
from core.utils import normalize_rut

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
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtener todos los usuarios del sistema (incluyendo administradores)
        funcionarios = CustomUser.objects.filter(
            role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA', 'ADMIN']
        ).order_by('last_name', 'first_name')

        # Preparar datos con horarios
        funcionarios_data = []
        con_horario = 0
        sin_horario = 0

        for func in funcionarios:
            horario = HorarioFuncionario.objects.filter(funcionario=func, activo=True).first()
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
        return context


class MiAsistenciaView(LoginRequiredMixin, TemplateView):
    """Vista para que usuarios vean su propia asistencia (todos los roles pueden ver la suya)"""
    template_name = 'asistencia/mi_asistencia.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtener parámetros de filtro
        mes = self.request.GET.get('mes')
        anio = self.request.GET.get('anio')

        if not mes or not anio:
            now = datetime.now()
            mes = str(now.month)
            anio = str(now.year)

        # Filtrar registros del usuario actual
        registros = RegistroAsistencia.objects.filter(
            funcionario=self.request.user,
            fecha__year=anio,
            fecha__month=mes
        ).order_by('-fecha')

        # Agregar horas trabajadas a cada registro para el template
        for registro in registros:
            if registro.minutos_trabajados:
                registro.horas_trabajadas = round(registro.minutos_trabajados / 60, 1)
            else:
                registro.horas_trabajadas = None

        # Si no hay registros para el período seleccionado, intentar con el último período con datos
        if not registros.exists() and not mes and not anio:
            ultimo_registro = RegistroAsistencia.objects.filter(
                funcionario=self.request.user
            ).order_by('-fecha').first()
            if ultimo_registro:
                mes = str(ultimo_registro.fecha.month)
                anio = str(ultimo_registro.fecha.year)
                registros = RegistroAsistencia.objects.filter(
                    funcionario=self.request.user,
                    fecha__year=anio,
                    fecha__month=mes
                ).order_by('-fecha')

        # Estadísticas del período
        total_dias = registros.count()
        dias_puntuales = registros.filter(estado='PUNTUAL').count()
        dias_retraso = registros.filter(estado='RETRASO').count()
        dias_ausente = registros.filter(estado='AUSENTE').count()

        # Estadísticas de tiempo trabajado (solo si el campo existe)
        tiempo_promedio_trabajado = 0
        dias_con_tiempo_trabajado = 0
        registros_con_tiempo = registros.none()  # Inicializar con queryset vacío
        total_horas_trabajadas_mes = 0
        total_minutos_retraso_mes = 0

        # Verificar si el campo minutos_trabajados existe en el modelo
        if hasattr(RegistroAsistencia, 'minutos_trabajados'):
            try:
                registros_con_tiempo = registros.exclude(minutos_trabajados__isnull=True)
                dias_con_tiempo_trabajado = registros_con_tiempo.count()
                if registros_con_tiempo.exists():
                    tiempo_promedio_trabajado = round(registros_con_tiempo.aggregate(
                        avg=Avg('minutos_trabajados')
                    )['avg'] or 0, 0)

                    # Calcular total de horas trabajadas en el mes
                    total_minutos_mes = registros_con_tiempo.aggregate(
                        total=Sum('minutos_trabajados')
                    )['total'] or 0
                    total_horas_trabajadas_mes = round(total_minutos_mes / 60, 1)

                # Calcular total de minutos de retraso en el mes
                registros_con_retraso = registros.exclude(minutos_retraso__isnull=True).filter(minutos_retraso__gt=0)
                total_minutos_retraso_mes = registros_con_retraso.aggregate(
                    total=Sum('minutos_retraso')
                )['total'] or 0

            except:
                # Si hay error (campo no existe), usar valores por defecto
                registros_con_tiempo = registros.none()
                dias_con_tiempo_trabajado = 0
                tiempo_promedio_trabajado = 0
                total_horas_trabajadas_mes = 0
                total_minutos_retraso_mes = 0

        # Calcular horas semanales efectivas
        horas_semanales = {}
        if registros_con_tiempo.exists():
            # Obtener el primer día del mes
            primer_dia_mes = datetime(int(anio), int(mes), 1).date()

            # Calcular semanas del mes
            for semana in range(5):  # Máximo 5 semanas en un mes
                inicio_semana = primer_dia_mes + timedelta(days=semana * 7)
                fin_semana = inicio_semana + timedelta(days=6)

                # Si la semana se sale del mes, ajustar
                ultimo_dia_mes = (primer_dia_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                if fin_semana > ultimo_dia_mes:
                    fin_semana = ultimo_dia_mes

                # Filtrar registros de esta semana
                registros_semana = registros_con_tiempo.filter(
                    fecha__gte=inicio_semana,
                    fecha__lte=fin_semana
                )

                if registros_semana.exists():
                    minutos_semana = registros_semana.aggregate(
                        total=Sum('minutos_trabajados')
                    )['total'] or 0
                    horas_semana = round(minutos_semana / 60, 1)
                    horas_semanales[f"Semana {semana + 1}"] = horas_semana

        # Meses y años disponibles
        context['meses'] = [
            (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
            (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
            (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
        ]
        context['anios_disponibles'] = RegistroAsistencia.objects.filter(
            funcionario=self.request.user
        ).values_list('fecha__year', flat=True).distinct().order_by('-fecha__year')

        context.update({
            'registros': registros,
            'mes': mes,
            'anio': anio,
            'estadisticas': {
                'total_dias': total_dias,
                'dias_puntuales': dias_puntuales,
                'dias_retraso': dias_retraso,
                'dias_ausente': dias_ausente,
                'porcentaje_puntualidad': round((dias_puntuales / total_dias * 100) if total_dias > 0 else 0, 1),
                'dias_con_tiempo_trabajado': registros_con_tiempo.count(),
                'tiempo_promedio_trabajado': tiempo_promedio_trabajado,
                'total_horas_trabajadas_mes': total_horas_trabajadas_mes,
                'total_minutos_retraso_mes': total_minutos_retraso_mes,
                'horas_semanales': horas_semanales,
            }
        })

        return context

class CargaHorariosView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Vista para cargar archivos Excel de horarios de funcionarios"""
    template_name = "asistencia/carga_horarios.html"
    form_class = CargaHorariosForm
    success_url = "/asistencia/admin/horarios/"

    def test_func(self):
        return self.request.user.role in ["ADMIN", "SECRETARIA"]

    def form_valid(self, form):
        archivo_excel = form.cleaned_data["archivo_excel"]

        try:
            # Procesar el archivo Excel
            horarios_creados, errores = self.procesar_excel_horarios(archivo_excel)

            if horarios_creados > 0:
                messages.success(
                    self.request,
                    f"Se procesaron correctamente {horarios_creados} horarios de funcionarios."
                )
            else:
                messages.warning(self.request, "No se encontraron horarios válidos para procesar.")

            if errores:
                for error in errores[:5]:  # Mostrar máximo 5 errores
                    messages.warning(self.request, error)
                if len(errores) > 5:
                    messages.warning(self.request, f"... y {len(errores) - 5} errores más.")

        except Exception as e:
            messages.error(self.request, f"Error al procesar el archivo: {str(e)}")
            return self.form_invalid(form)

        return super().form_valid(form)

    def procesar_excel_horarios(self, archivo_excel):
        """Procesa el archivo Excel y crea horarios de funcionarios"""
        rows = load_data_file(archivo_excel, None, None)

        horarios_creados = 0
        errores = []

        # Procesar cada fila
        for row_num, row in enumerate(rows, start=2):
            if not any(row):  # Skip empty rows
                continue

            try:
                # Asumir formato: RUT, Hora_Entrada, Tolerancia
                # Ajustar según el formato real del Excel
                rut, hora_entrada_str, tolerancia_str = row[:3]

                if not rut or not hora_entrada_str:
                    errores.append(f"Fila {row_num}: Faltan datos obligatorios (RUT o hora de entrada)")
                    continue

                # Convertir RUT a string para procesamiento consistente
                rut_str = str(rut).strip()

                # Buscar funcionario por RUT usando función robusta
                funcionario = find_user_by_rut(rut_str)
                if not funcionario:
                    errores.append(f"Fila {row_num}: No se encontró funcionario con RUT {rut_str}")
                    continue

                # Parsear hora
                if isinstance(hora_entrada_str, str):
                    try:
                        hora_entrada = datetime.strptime(hora_entrada_str, "%H:%M:%S").time()
                    except ValueError:
                        hora_entrada = datetime.strptime(hora_entrada_str, "%H:%M").time()
                else:
                    hora_entrada = hora_entrada_str

                # Parsear tolerancia (opcional, default 15)
                tolerancia = 15  # default
                if tolerancia_str:
                    try:
                        tolerancia = int(tolerancia_str)
                    except (ValueError, TypeError):
                        pass  # usar default

                # Crear o actualizar horario
                horario, created = HorarioFuncionario.objects.get_or_create(
                    funcionario=funcionario,
                    defaults={
                        "hora_entrada": hora_entrada,
                        "tolerancia_minutos": tolerancia,
                        "activo": True,
                    }
                )

                if not created:
                    # Actualizar si ya existe
                    horario.hora_entrada = hora_entrada
                    horario.tolerancia_minutos = tolerancia
                    horario.activo = True
                    horario.save()

                horarios_creados += 1

            except Exception as e:
                errores.append(f"Fila {row_num}: Error procesando fila - {str(e)}")

        return horarios_creados, errores


class GestionAsistenciaView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Vista administrativa para gestionar usuarios con asistencia (similar a gestion_liquidaciones pero mostrando usuarios)"""
    model = CustomUser
    template_name = 'asistencia/gestion_asistencia.html'
    context_object_name = 'usuarios'
    paginate_by = 20

    def test_func(self):
        # Solo administradores, secretarias, directores y directivos pueden ver la gestión
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR', 'DIRECTIVO']

    def get_queryset(self):
        # Obtener usuarios que tienen registros de asistencia
        usuarios_con_asistencia = RegistroAsistencia.objects.values_list('funcionario_id', flat=True).distinct()

        queryset = CustomUser.objects.filter(
            id__in=usuarios_con_asistencia,
            role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA', 'ADMIN']
        )

        # Filtros
        search = self.request.GET.get('search')

        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(run__icontains=search)
            )

        # Aplicar ordenamiento
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
            queryset = queryset.order_by('role', 'last_name', 'first_name')
        elif sort_by == 'role_desc':
            queryset = queryset.order_by('-role', 'last_name', 'first_name')
        else:
            queryset = queryset.order_by('last_name', 'first_name')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Estadísticas generales
        total_usuarios = RegistroAsistencia.objects.values('funcionario_id').distinct().count()
        total_registros = RegistroAsistencia.objects.count()
        registros_puntuales = RegistroAsistencia.objects.filter(estado='PUNTUAL').count()
        registros_retraso = RegistroAsistencia.objects.filter(estado='RETRASO').count()
        registros_ausentes = RegistroAsistencia.objects.filter(estado='AUSENTE').count()

        context['estadisticas'] = {
            'total_usuarios': total_usuarios,
            'total_registros': total_registros,
            'registros_puntuales': registros_puntuales,
            'registros_retraso': registros_retraso,
            'registros_ausentes': registros_ausentes,
            'porcentaje_puntualidad': round((registros_puntuales / total_registros * 100) if total_registros > 0 else 0, 1)
        }

        # Para cada usuario, agregar estadísticas
        usuarios_con_stats = []
        for usuario in context['usuarios']:
            # Estadísticas del usuario
            registros_usuario = RegistroAsistencia.objects.filter(funcionario=usuario)
            total_registros_usuario = registros_usuario.count()
            registros_puntuales_usuario = registros_usuario.filter(estado='PUNTUAL').count()

            # Último registro
            ultimo_registro = registros_usuario.order_by('-fecha').first()

            usuarios_con_stats.append({
                'usuario': usuario,
                'total_registros': total_registros_usuario,
                'registros_puntuales': registros_puntuales_usuario,
                'porcentaje_puntualidad': round((registros_puntuales_usuario / total_registros_usuario * 100) if total_registros_usuario > 0 else 0, 1),
                'ultimo_registro': ultimo_registro.fecha if ultimo_registro else None,
            })

        context['usuarios_con_stats'] = usuarios_con_stats

        # Filtros aplicados
        context['filtros_aplicados'] = {
            'search': self.request.GET.get('search'),
        }
        context['current_sort'] = self.request.GET.get('sort', 'name')

        return context


class CargaRegistrosAsistenciaView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Vista para cargar registros de asistencia desde vouchers del reloj control"""
    template_name = "asistencia/carga_registros.html"
    form_class = CargaRegistrosAsistenciaForm
    success_url = "/asistencia/gestion/"

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

    def form_valid(self, form):
        archivo_excel = form.cleaned_data["archivo_excel"]
        mes = form.cleaned_data.get("mes")
        anio = form.cleaned_data.get("anio")

        try:
            # Procesar el archivo
            registros_creados, errores = self.procesar_excel_asistencia(archivo_excel, mes, anio)

            if registros_creados > 0:
                messages.success(
                    self.request,
                    f"Se procesaron correctamente {registros_creados} registros de asistencia."
                )
            else:
                messages.warning(self.request, "No se encontraron registros válidos para procesar.")

            if errores:
                for error in errores[:5]:  # Mostrar máximo 5 errores
                    messages.warning(self.request, error)
                if len(errores) > 5:
                    messages.warning(self.request, f"... y {len(errores) - 5} errores más.")

        except Exception as e:
            messages.error(self.request, f"Error al procesar el archivo: {str(e)}")
            return self.form_invalid(form)

        return super().form_valid(form)

    def procesar_excel_asistencia(self, archivo_excel, mes=None, anio=None):
        """Procesa el archivo Excel de registros del reloj control con soporte para múltiples formatos de fecha y hora"""
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

                # Determinar entrada y salida basándose en las horas
                hora_entrada = None
                hora_salida = None

                if len(horas_ordenadas) == 1:
                    # Solo una hora: si es antes del mediodía, entrada; si después, salida
                    hora_unica = horas_ordenadas[0]
                    if hora_unica.hour < 12:
                        hora_entrada = hora_unica
                    else:
                        hora_salida = hora_unica
                elif len(horas_ordenadas) >= 2:
                    # Múltiples horas: primera antes del mediodía = entrada, última después del mediodía = salida
                    horas_manana = [h for h in horas_ordenadas if h.hour < 12]
                    horas_tarde = [h for h in horas_ordenadas if h.hour >= 12]

                    if horas_manana:
                        hora_entrada = horas_manana[0]  # Primera hora de la mañana

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
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

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
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

    def form_valid(self, form):
        messages.success(self.request, f'Horario actualizado exitosamente para {form.instance.funcionario.get_full_name()}')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('asistencia:gestion_horarios')


class ToggleHorarioView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para activar/desactivar horario"""

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

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

        # Agrupar registros por año
        registros_por_anio = {}
        anios_disponibles = registros_usuario.values_list('fecha__year', flat=True).distinct().order_by('-fecha__year')

        for anio in anios_disponibles:
            registros_anio = registros_usuario.filter(fecha__year=anio).order_by('-fecha')

            # Agrupar por mes dentro del año
            registros_por_mes = {}
            meses_con_datos = registros_anio.values_list('fecha__month', flat=True).distinct().order_by('fecha__month')

            for mes in meses_con_datos:
                registros_mes = registros_anio.filter(fecha__month=mes).order_by('fecha')
                registros_por_mes[mes] = {
                    'registros': registros_mes,
                    'total': registros_mes.count(),
                    'puntuales': registros_mes.filter(estado='PUNTUAL').count(),
                    'retrasos': registros_mes.filter(estado='RETRASO').count(),
                    'ausentes': registros_mes.filter(estado='AUSENTE').count(),
                }

            registros_por_anio[anio] = {
                'registros_por_mes': registros_por_mes,
                'total_anio': registros_anio.count(),
                'puntuales_anio': registros_anio.filter(estado='PUNTUAL').count(),
            }

        # Horario asignado
        horario_actual = HorarioFuncionario.objects.filter(
            funcionario=usuario, activo=True
        ).first()

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
            'estadisticas_funcionario': {
                'total_registros': total_registros,
                'registros_puntuales': registros_puntuales,
                'registros_retraso': registros_retraso,
                'registros_ausentes': registros_ausentes,
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
    template_name = 'asistencia/crear_festivo.html'
    fields = ['fecha', 'nombre', 'descripcion']
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
                elif registro.estado == 'AUSENTE':
                    inasistencia_info = {
                        'fecha': registro.fecha,
                        'hora_esperada': registro.horario_asignado.hora_entrada if registro.horario_asignado else None,
                    }
                    func_data['inasistencias'].append(inasistencia_info)
                elif registro.estado == 'JUSTIFICADO':
                    justificado_info = {
                        'fecha': registro.fecha,
                        'tipo': 'permiso' if registro.tiene_permiso_aprobado() else 'licencia' if registro.tiene_licencia_medica() else 'otro',
                    }
                    func_data['justificados'].append(justificado_info)

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


class ReporteAsistenciaIndividualView(LoginRequiredMixin, View):
    """Vista para generar reporte individual de asistencia en PDF"""

    def get(self, request, anio, mes):
        # Obtener datos del usuario actual para el mes
        registros_mes = RegistroAsistencia.objects.filter(
            funcionario=request.user,
            fecha__year=anio,
            fecha__month=mes
        ).select_related('horario_asignado').order_by('fecha')

        # Recopilar detalles de atrasos, inasistencias y justificaciones
        atrasos_detalle = []
        inasistencias_detalle = []
        justificaciones_detalle = []

        for registro in registros_mes:
            if registro.estado == 'RETRASO':
                atraso_info = {
                    'fecha': registro.fecha,
                    'hora_entrada': registro.hora_entrada_real,
                    'minutos_retraso': registro.minutos_retraso,
                }
                atrasos_detalle.append(atraso_info)
            elif registro.estado == 'AUSENTE':
                inasistencia_info = {
                    'fecha': registro.fecha,
                    'hora_esperada': registro.horario_asignado.hora_entrada if registro.horario_asignado else None,
                }
                inasistencias_detalle.append(inasistencia_info)
            elif registro.estado in ['JUSTIFICADO', 'DIA_ADMINISTRATIVO', 'LICENCIA_MEDICA']:
                # Determinar el tipo de justificación basado en el estado
                if registro.estado == 'DIA_ADMINISTRATIVO':
                    tipo = 'permiso'
                elif registro.estado == 'LICENCIA_MEDICA':
                    tipo = 'licencia'
                else:
                    tipo = 'permiso' if registro.tiene_permiso_aprobado() else 'licencia' if registro.tiene_licencia_medica() else 'otro'

                justificacion_info = {
                    'fecha': registro.fecha,
                    'tipo': tipo,
                }
                justificaciones_detalle.append(justificacion_info)

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
            'fecha_actual': datetime.now(),
        })

        # Generar PDF
        pdf_file = HTML(string=html_content).write_pdf()

        # Crear respuesta HTTP
        response = HttpResponse(pdf_file, content_type='application/pdf')
        filename = f'mi_asistencia_{anio}_{mes:02d}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

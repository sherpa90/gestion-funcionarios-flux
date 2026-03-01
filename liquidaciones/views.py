import io
import re
import zipfile
import logging
import pypdf
from django.shortcuts import render, redirect
from django.views.generic import FormView, ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import HttpResponse
from django.utils.html import escape
from .forms import CargaLiquidacionesForm
from .models import Liquidacion
from .services import PayrollService, PayrollValidationService
from users.models import CustomUser
from core.utils import normalize_rut, clean_rut_for_matching

# Configurar logging
logger = logging.getLogger(__name__)

class CargaLiquidacionesView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'liquidaciones/carga_form.html'
    form_class = CargaLiquidacionesForm
    success_url = '/liquidaciones/carga/'

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR']

    def form_valid(self, form):
        archivo = form.cleaned_data['archivo']
        mes = form.cleaned_data['mes']
        anio = form.cleaned_data['anio']

        # Obtener lista de RUTs existentes para comparación
        usuarios_existentes = list(CustomUser.objects.values_list('run', flat=True))

        try:
            logger.info(f"Starting PDF processing for user {self.request.user.get_full_name()}, file: {archivo.name}, month: {mes}, year: {anio}")

            try:
                pdf_reader = pypdf.PdfReader(archivo)
                logger.info(f"PDF loaded successfully. Pages: {len(pdf_reader.pages)}")
            except pypdf.errors.PdfReadError as e:
                logger.error(f"PDF read error: {e}")
                messages.error(self.request, "El archivo PDF está corrupto o no es un archivo PDF válido.")
                return self.form_invalid(form)
            except Exception as e:
                logger.error(f"Unexpected error loading PDF: {e}")
                messages.error(self.request, "Error al cargar el archivo PDF.")
                return self.form_invalid(form)

            processed_count = 0
            errors = []

            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if not text.strip():
                        logger.warning(f"Page {page_num + 1}: Empty or no text extracted")
                        continue

                    # Buscar RUT en el texto - múltiples formatos posibles
                    rut_patterns = [
                        r'(\d{7,8}-[\dKk])',  # 12345678-9
                        r'(\d{1,2}\.\d{3}\.\d{3}-[\dKk])',  # 12.345.678-9
                        r'(\d{1,2}\s+\d{3}\s+\d{3}-[\dKk])',  # 12 345 678-9
                        r'RUT[:\s]*(\d{7,8}-[\dKk])',  # RUT: 12345678-9
                        r'RUT[:\s]*(\d{1,2}\.\d{3}\.\d{3}-[\dKk])',  # RUT: 12.345.678-9
                        r'(\d{8,9})',  # 123456789 (sin guión)
                    ]

                    rut_encontrado = None
                    for pattern in rut_patterns:
                        match = re.search(pattern, text)
                        if match:
                            rut_encontrado = match.group(1)
                            break

                    if rut_encontrado:
                        logger.info(f"Page {page_num + 1}: Found RUT '{rut_encontrado}'")

                        # Normalizar el RUT encontrado al formato estándar
                        rut_normalizado = normalize_rut(rut_encontrado)
                        logger.debug(f"RUT normalized: '{rut_encontrado}' -> '{rut_normalizado}'")

                        try:
                            # Usar servicio para encontrar usuario
                            usuario = PayrollService.find_user_by_rut(rut_encontrado)

                            if usuario:
                                logger.info(f"User matched: {usuario.get_full_name()} (RUT: {usuario.run})")

                                # VALIDAR: Verificar que no exista una liquidación para ese mes/año
                                from .services import PayrollValidationService
                                puede_subir, msg_error = PayrollValidationService.can_upload_payroll(
                                    self.request.user, usuario, mes, anio
                                )
                                if not puede_subir:
                                    logger.warning(f"Page {page_num + 1}: {msg_error}")
                                    errors.append(f"Página {page_num + 1}: {msg_error}")
                                    continue

                                # Usar servicio para crear liquidación
                                # Necesitamos el contenido completo del PDF para extraer la página
                                archivo.seek(0)  # Reset file pointer
                                pdf_content = archivo.read()

                                liquidacion = PayrollService.create_payroll_from_pdf(
                                    pdf_content=pdf_content,
                                    user=usuario,
                                    month=mes,
                                    year=anio,
                                    page_num=page_num
                                )

                                if liquidacion:
                                    processed_count += 1
                                else:
                                    errors.append(f"Página {page_num + 1}: Error creando liquidación para {usuario.get_full_name()}")
                            else:
                                logger.warning(f"User not found for RUT: {rut_encontrado} (normalized: {rut_normalizado})")
                                errors.append(f"Página {page_num + 1}: RUT '{rut_encontrado}' no encontrado. Asegúrese de que el usuario esté registrado en el sistema.")
                        except Exception as e:
                            logger.error(f"Error processing user for page {page_num + 1}: {e}")
                            errors.append(f"Página {page_num + 1}: Error procesando usuario ({str(e)})")
                    else:
                        logger.debug(f"Page {page_num + 1}: No RUT found in text")
                        # No agregar error, simplemente continuar con la siguiente página

                except Exception as e:
                    logger.error(f"Error processing page {page_num + 1}: {e}")
                    errors.append(f"Página {page_num + 1}: Error procesando página ({str(e)})")

            if processed_count > 0:
                logger.info(f"PDF processing completed successfully. Processed: {processed_count} liquidations")
                messages.success(self.request, f"Se procesaron correctamente {processed_count} liquidaciones. Las páginas sin RUT válido fueron omitidas.")
            else:
                logger.warning("No valid liquidations found in PDF")
                messages.warning(self.request, "No se encontraron liquidaciones válidas en el archivo. Verifique que los RUTs estén en formato correcto.")

            if errors:
                logger.warning(f"Processing errors: {len(errors)}")
                # IMPORTANT: Escape HTML to prevent XSS attacks
                errors_escaped = ['<br>'.join([escape(str(e)) for e in error.split('<br>')]) for error in errors[:5]]
                messages.warning(self.request, f"Problemas encontrados: <br>" + "<br>".join(errors_escaped))
                if len(errors) > 5:
                    messages.warning(self.request, f"... y {len(errors) - 5} problemas más.")

        except Exception as e:
            logger.exception(f"Critical error in PDF processing: {e}")
            messages.error(self.request, "Error interno del servidor al procesar el archivo. Contacte al administrador.")
            return self.form_invalid(form)

        return super().form_valid(form)

class MisLiquidacionesView(LoginRequiredMixin, ListView):
    model = Liquidacion
    template_name = 'liquidaciones/mis_liquidaciones.html'
    context_object_name = 'liquidaciones'
    paginate_by = 12

    def get_queryset(self):
        # Ordenar por fecha completa: primero año descendente, luego mes descendente
        # Esto muestra las liquidaciones más recientes primero
        return Liquidacion.objects.filter(funcionario=self.request.user).order_by('-anio', '-mes')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Usar servicio para obtener liquidaciones por año
        context['liquidaciones_por_anio'] = PayrollService.get_user_payrolls_by_year(self.request.user)

        # Usar servicio para estadísticas
        context['estadisticas'] = PayrollService.get_payroll_statistics(self.request.user)

        return context


class DescargarTodasLiquidacionesView(LoginRequiredMixin, View):
    """Vista para descargar todas las liquidaciones del usuario como ZIP"""

    def get(self, request):
        liquidaciones = Liquidacion.objects.filter(funcionario=request.user).order_by('-anio', '-mes')

        if not liquidaciones:
            messages.warning(request, 'No tienes liquidaciones disponibles para descargar.')
            return redirect('mis_liquidaciones')

        # Crear archivo ZIP en memoria
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for liquidacion in liquidaciones:
                # Leer el archivo PDF
                with liquidacion.archivo.open('rb') as pdf_file:
                    pdf_data = pdf_file.read()

                # Nombre del archivo en el ZIP
                filename = f"liquidacion_{liquidacion.anio}_{liquidacion.mes:02d}_{request.user.run}.pdf"
                zip_file.writestr(filename, pdf_data)

        zip_buffer.seek(0)

        # Crear respuesta HTTP
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename=liquidaciones_{request.user.run}.zip'

        return response


class DescargarLiquidacionesAnioView(LoginRequiredMixin, View):
    """Vista para descargar todas las liquidaciones de un año específico como ZIP"""

    def get(self, request, anio):
        liquidaciones = Liquidacion.objects.filter(
            funcionario=request.user,
            anio=anio
        ).order_by('-mes')

        if not liquidaciones:
            messages.warning(request, f'No tienes liquidaciones disponibles para el año {anio}.')
            return redirect('mis_liquidaciones')

        # Crear archivo ZIP en memoria
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for liquidacion in liquidaciones:
                # Leer el archivo PDF
                with liquidacion.archivo.open('rb') as pdf_file:
                    pdf_data = pdf_file.read()

                # Nombre del archivo en el ZIP
                filename = f"liquidacion_{liquidacion.anio}_{liquidacion.mes:02d}_{request.user.run}.pdf"
                zip_file.writestr(filename, pdf_data)

        zip_buffer.seek(0)

        # Crear respuesta HTTP
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename=liquidaciones_{anio}_{request.user.run}.zip'

        return response


class GestionLiquidacionesView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Vista administrativa para gestionar todas las liquidaciones del sistema"""
    model = Liquidacion
    template_name = 'liquidaciones/gestion_liquidaciones.html'
    context_object_name = 'liquidaciones'
    paginate_by = 20

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

    def get_queryset(self):
        queryset = Liquidacion.objects.select_related('funcionario').order_by('-anio', '-mes', 'funcionario__last_name')

        # Filtros
        usuario_id = self.request.GET.get('usuario')
        anio = self.request.GET.get('anio')
        mes = self.request.GET.get('mes')
        search = self.request.GET.get('search')

        if usuario_id:
            queryset = queryset.filter(funcionario_id=usuario_id)
        if anio:
            queryset = queryset.filter(anio=anio)
        if mes:
            queryset = queryset.filter(mes=mes)
        if search:
            queryset = queryset.filter(
                Q(funcionario__first_name__icontains=search) |
                Q(funcionario__last_name__icontains=search) |
                Q(funcionario__run__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Usuarios para filtro
        context['usuarios'] = CustomUser.objects.filter(role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA']).order_by('last_name', 'first_name')

        # Años disponibles
        context['anios_disponibles'] = Liquidacion.objects.values_list('anio', flat=True).distinct().order_by('-anio')

        # Meses para filtro
        context['mes_choices'] = [
            (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
            (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
            (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
        ]

        # Estadísticas
        total_liquidaciones = Liquidacion.objects.count()
        total_usuarios_con_liquidaciones = Liquidacion.objects.values('funcionario').distinct().count()

        context['estadisticas'] = {
            'total_liquidaciones': total_liquidaciones,
            'total_usuarios': total_usuarios_con_liquidaciones,
            'promedio_por_usuario': round(total_liquidaciones / total_usuarios_con_liquidaciones, 1) if total_usuarios_con_liquidaciones > 0 else 0
        }

        # Filtros aplicados
        context['filtros_aplicados'] = {
            'usuario': self.request.GET.get('usuario'),
            'anio': self.request.GET.get('anio'),
            'mes': self.request.GET.get('mes'),
            'search': self.request.GET.get('search'),
        }

        return context


class AdminLiquidacionesOverviewView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Vista para administradores: Lista de todos los funcionarios con liquidaciones"""
    model = CustomUser
    template_name = 'liquidaciones/admin_liquidaciones_overview.html'
    context_object_name = 'funcionarios'
    paginate_by = 20

    def test_func(self):
        return self.request.user.role == 'ADMIN'

    def get_queryset(self):
        # Obtener todos los usuarios del sistema (sin filtro de liquidaciones)
        # Mostrar todos los roles incluyendo ADMIN
        queryset = CustomUser.objects.filter(
            role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA', 'ADMIN']
        )

        # Aplicar ordenamiento
        sort_by = self.request.GET.get('sort', 'name')
        if sort_by == 'name':
            queryset = queryset.order_by('last_name', 'first_name')
        elif sort_by == 'name_desc':
            queryset = queryset.order_by('-last_name', '-first_name')
        elif sort_by == 'role':
            queryset = queryset.order_by('role', 'last_name', 'first_name')
        elif sort_by == 'role_desc':
            queryset = queryset.order_by('-role', 'last_name', 'first_name')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Optimizar queries usando prefetch_related para evitar N+1
        funcionarios_ids = [f.id for f in context['funcionarios']]
        liquidaciones_por_usuario = {}

        # Obtener todas las liquidaciones de una vez con prefetch
        liquidaciones_qs = Liquidacion.objects.filter(
            funcionario_id__in=funcionarios_ids
        ).select_related('funcionario').order_by('funcionario_id', '-anio', '-mes')

        # Agrupar liquidaciones por usuario
        for liquidacion in liquidaciones_qs:
            user_id = liquidacion.funcionario_id
            if user_id not in liquidaciones_por_usuario:
                liquidaciones_por_usuario[user_id] = []
            liquidaciones_por_usuario[user_id].append(liquidacion)

        # Construir la información de funcionarios
        funcionarios_con_info = []
        for funcionario in context['funcionarios']:
            user_liquidaciones = liquidaciones_por_usuario.get(funcionario.id, [])
            funcionarios_con_info.append({
                'usuario': funcionario,
                'total_liquidaciones': len(user_liquidaciones),
                'ultima_liquidacion': user_liquidaciones[0] if user_liquidaciones else None,
                'anios': list(set(l.anio for l in user_liquidaciones))
            })

        context['funcionarios_con_info'] = funcionarios_con_info

        # Información de ordenamiento
        context['current_sort'] = self.request.GET.get('sort', 'name')

        return context


class AdminFuncionarioLiquidacionesView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Vista para administradores: Liquidaciones detalladas de un funcionario específico"""
    model = Liquidacion
    template_name = 'liquidaciones/admin_funcionario_liquidaciones.html'
    context_object_name = 'liquidaciones'
    paginate_by = 12

    def test_func(self):
        return self.request.user.role == 'ADMIN'

    def get_queryset(self):
        funcionario_id = self.kwargs['funcionario_id']
        return Liquidacion.objects.filter(funcionario_id=funcionario_id).order_by('-anio', '-mes')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        funcionario_id = self.kwargs['funcionario_id']
        context['funcionario'] = CustomUser.objects.get(id=funcionario_id)

        # Agrupar liquidaciones por año
        liquidaciones_por_anio = {}
        for liquidacion in context['liquidaciones']:
            anio = liquidacion.anio
            if anio not in liquidaciones_por_anio:
                liquidaciones_por_anio[anio] = []
            liquidaciones_por_anio[anio].append(liquidacion)

        context['liquidaciones_por_anio'] = dict(sorted(liquidaciones_por_anio.items(), reverse=True))

        # Estadísticas del funcionario
        total_liquidaciones = context['liquidaciones'].count()
        anios_con_liquidaciones = len(liquidaciones_por_anio)

        context['estadisticas_funcionario'] = {
            'total_liquidaciones': total_liquidaciones,
            'anios_con_liquidaciones': anios_con_liquidaciones,
            'promedio_por_anio': round(total_liquidaciones / anios_con_liquidaciones, 1) if anios_con_liquidaciones > 0 else 0
        }

        return context


class AdminEliminarLiquidacionView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para que administradores eliminen liquidaciones específicas"""

    def test_func(self):
        return self.request.user.role == 'ADMIN'

    def post(self, request, liquidacion_id):
        try:
            liquidacion = Liquidacion.objects.get(id=liquidacion_id)
            funcionario = liquidacion.funcionario

            # Eliminar el archivo físico si existe
            if liquidacion.archivo:
                liquidacion.archivo.delete()

            # Eliminar el registro de la base de datos
            liquidacion.delete()

            messages.success(
                request,
                f'Liquidación {liquidacion.mes}/{liquidacion.anio} de {funcionario.get_full_name()} eliminada exitosamente.'
            )

        except Liquidacion.DoesNotExist:
            messages.error(request, 'La liquidación especificada no existe.')

        # Redirigir de vuelta a la vista del funcionario
        return redirect(request.META.get('HTTP_REFERER', 'admin_liquidaciones_overview'))

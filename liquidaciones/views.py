import io
import re
import zipfile
import logging
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Recuperar resultado de la sesión si existe
        if 'carga_resultado' in self.request.session:
            context['resultado'] = self.request.session.pop('carga_resultado')
        return context

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA', 'DIRECTOR']

    def form_valid(self, form):
        archivo = form.cleaned_data['archivo']
        mes = int(form.cleaned_data['mes'])
        anio = int(form.cleaned_data['anio'])

        # Obtener lista de RUTs existentes para comparación
        usuarios_existentes = list(CustomUser.objects.values_list('run', flat=True))

        try:
            logger.info(f"Starting PDF processing for user {self.request.user.get_full_name()}, file: {archivo.name}, month: {mes}, year: {anio}")

            import pypdf
            try:
                if hasattr(archivo, 'seek'):
                    archivo.seek(0)
                pdf_bytes = archivo.read()
                pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
                total_pages = len(pdf_reader.pages)
                logger.info(f"PDF loaded successfully with pypdf. Pages: {total_pages}")
            except Exception as e:
                logger.error(f"PDF read error with pypdf: {e}")
                messages.error(self.request, "El archivo PDF no se pudo leer correctamente.")
                return self.form_invalid(form)

            processed_count = 0
            errors = []

            for page_num in range(total_pages):
                try:
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text() or ""
                    text = text.strip()
                    
                    # Si pypdf no extrae texto, intentar con pdfminer.six (más robusto)
                    if not text:
                        logger.info(f"Page {page_num + 1}: pypdf returned empty text, trying pdfminer")
                        try:
                            from pdfminer.high_level import extract_text
                            from pdfminer.layout import LAParams
                            
                            archivo.seek(0)
                            # Intentar con parámetros más agresivos
                            laparams = LAParams(
                                line_margin=0.5,
                                char_margin=2.0,
                                word_margin=0.1
                            )
                            text = extract_text(
                                io.BytesIO(pdf_bytes),
                                page_numbers=[page_num],
                                laparams=laparams
                            ).strip()
                            logger.info(f"Page {page_num + 1}: pdfminer extracted {len(text)} characters")
                        except Exception as pdfminer_error:
                            logger.debug(f"Page {page_num + 1}: pdfminer failed: {pdfminer_error}")
                    
                    # Si pdfminer falla, intentar con pdfplumber
                    if not text:
                        logger.info(f"Page {page_num + 1}: Trying pdfplumber")
                        try:
                            import pdfplumber
                            archivo.seek(0)
                            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                                if page_num < len(pdf.pages):
                                    page_plumber = pdf.pages[page_num]
                                    # Intentar diferentes métodos de extracción
                                    text = page_plumber.extract_text(
                                        x_tolerance=3,
                                        y_tolerance=3,
                                        keep_blank_chars=False
                                    ) or ""
                                    # Si aún no hay texto, intentar extraer palabras
                                    if not text.strip():
                                        words = page_plumber.extract_words()
                                        text = " ".join([w.get('text', '') for w in words])
                                    text = text.strip()
                                    logger.info(f"Page {page_num + 1}: pdfplumber extracted {len(text)} characters")
                        except Exception as plumber_error:
                            logger.debug(f"Page {page_num + 1}: pdfplumber failed: {plumber_error}")
                    
                    # Si todo falla, intentar con fitz (PyMuPDF) como último método sin OCR
                    if not text:
                        logger.info(f"Page {page_num + 1}: Trying fitz (PyMuPDF)")
                        try:
                            import fitz
                            archivo.seek(0)
                            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
                            if page_num < len(pdf_document):
                                page_fitz = pdf_document[page_num]
                                text = page_fitz.get_text().strip()
                                logger.info(f"Page {page_num + 1}: fitz extracted {len(text)} characters")
                                pdf_document.close()
                        except Exception as fitz_error:
                            logger.warning(f"Page {page_num + 1}: fitz failed: {fitz_error}")
                    
                    # Si aún no hay texto, intentar OCR si las dependencias están disponibles
                    if not text:
                        logger.info(f"Page {page_num + 1}: All text extraction methods failed, trying OCR")
                        try:
                            import fitz
                            from pdf2image import convert_from_bytes
                            import pytesseract
                            from PIL import Image
                            
                            # Convertir página a imagen
                            archivo.seek(0)
                            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
                            if page_num < len(pdf_document):
                                page = pdf_document[page_num]
                                # Renderizar a 300 DPI para mejor OCR
                                zoom = 300 / 72
                                mat = fitz.Matrix(zoom, zoom)
                                pix = page.get_pixmap(matrix=mat)
                                
                                # Convertir a imagen PIL
                                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                
                                # Preprocesar imagen: convertir a escala de grises y mejorar contraste
                                img = img.convert('L')
                                
                                # Aplicar OCR
                                custom_config = r'--oem 3 --psm 6 -l spa'
                                text = pytesseract.image_to_string(img, config=custom_config)
                                text = text.strip()
                                logger.info(f"Page {page_num + 1}: OCR extracted {len(text)} characters")
                                pdf_document.close()
                        except ImportError as e:
                            logger.debug(f"OCR dependencies not available: {e}")
                        except Exception as ocr_error:
                            logger.warning(f"Page {page_num + 1}: OCR failed: {ocr_error}")

                    if not text:
                        logger.warning(f"Page {page_num + 1}: No text extracted after all methods")
                        errors.append(f"Página {page_num + 1}: No se pudo extraer texto. Verifique el formato del PDF.")
                        continue

                    # Buscar RUT en el texto - múltiples formatos posibles
                    # Agregamos patrones mucho más flexibles para capturar RUTs con espacios o formatos extraños
                    rut_patterns = [
                        r'(\d{1,2}[\s\.]?\d{3}[\s\.]?\d{3}[\s-]*[\dKk])', # Formato súper flexible (17.639.211-8 o 17 639 211 - 8)
                        r'(\d{7,8}-[\s]*[\dKk])',  # 12345678-9
                        r'(\d{1,2}\.\d{3}\.\d{3}-[\dKk])',  # 12.345.678-9
                        r'(\d{1,2}\s+\d{3}\s+\d{3}-[\dKk])',  # 12 345 678-9
                        r'RUT[:\s]*(\d{1,2}[\s\.]?\d{3}[\s\.]?\d{3}[\s-]*[\dKk])', # RUT con etiqueta
                        r'(\d{8,9})',  # 123456789 (sin guión)
                    ]

                    rut_encontrado = None
                    for pattern in rut_patterns:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            rut_encontrado = match.group(1)
                            break
                    
                    # Log para depuración si no se encuentra RUT en una página con texto
                    if not rut_encontrado:
                        logger.warning(f"Page {page_num + 1}: No RUT found with standard regex. Trying clean search...")
                        # Intento desesperado: remover espacios y puntos para buscar secuencia de dígitos
                        # Esto ayuda si el PDF separa los números por bloques o capas
                        text_limpio = re.sub(r'[\s\.]', '', text)
                        match_limpio = re.search(r'(\d{7,8}-?[\dKk])', text_limpio, re.IGNORECASE)
                        if match_limpio:
                            rut_encontrado = match_limpio.group(1)
                            logger.info(f"Page {page_num + 1}: Found RUT via clean search: {rut_encontrado}")

                    if not rut_encontrado:
                        logger.warning(f"Page {page_num + 1}: No RUT found. Text snippet: {text[:100].replace('\\n', ' ')}...")
                        errors.append(f"Página {page_num + 1}: No se encontró un RUT válido. Verifique que el documento tenga el formato correcto.")

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
                                # Ya tenemos pdf_bytes
                                pdf_content = pdf_bytes

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

            # Guardar resultados para mostrar en el template de forma elegante
            self.request.session['carga_resultado'] = {
                'success_count': processed_count,
                'error_count': len(errors),
                'errors': errors[:10],  # Mostrar máximo 10 errores de muestra
                'total_pages': total_pages
            }

            if processed_count > 0:
                logger.info(f"PDF processing completed successfully. Processed: {processed_count} liquidations")
                messages.success(self.request, "Proceso de carga finalizado.")
            elif not errors:
                messages.warning(self.request, "No se encontraron liquidaciones válidas en el archivo.")

        except Exception as e:
            logger.exception(f"Critical error in PDF processing: {e}")
            messages.error(self.request, "Error interno del servidor al procesar el archivo.")
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
        queryset = Liquidacion.objects.select_related('funcionario').order_by('funcionario__first_name', 'funcionario__last_name', '-anio', '-mes')

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
        context['usuarios'] = CustomUser.objects.filter(role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA']).order_by('first_name', 'last_name')

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
    # Sin paginacion - mostrar todos los usuarios

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

    def get_queryset(self):
        # Obtener todos los usuarios del sistema (sin filtro de liquidaciones)
        # Mostrar todos los roles incluyendo ADMIN
        queryset = CustomUser.objects.filter(
            role__in=['FUNCIONARIO', 'DIRECTOR', 'DIRECTIVO', 'SECRETARIA', 'ADMIN']
        )

        # Buscador
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(run__icontains=search_query) |
                Q(email__icontains=search_query)
            )

        # Aplicar ordenamiento
        sort_by = self.request.GET.get('sort') or 'name'
        if sort_by == 'name':
            queryset = queryset.order_by('first_name', 'last_name')
        elif sort_by == 'name_desc':
            queryset = queryset.order_by('-first_name', '-last_name')
        elif sort_by == 'role':
            queryset = queryset.order_by('role', 'first_name', 'last_name')
        elif sort_by == 'role_desc':
            queryset = queryset.order_by('-role', 'first_name', 'last_name')
        else:
            # Ordenamiento por defecto si el parámetro no coincide
            queryset = queryset.order_by('first_name', 'last_name')

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
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

    def get_queryset(self):
        funcionario_id = self.kwargs['funcionario_id']
        return Liquidacion.objects.filter(funcionario_id=funcionario_id).order_by('-anio', '-mes')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        funcionario_id = self.kwargs['funcionario_id']
        context['funcionario'] = CustomUser.objects.get(id=funcionario_id)

        # Obtener todas las liquidaciones sin paginación para las estadísticas
        todas_liquidaciones = Liquidacion.objects.filter(funcionario_id=funcionario_id).order_by('-anio', '-mes')
        
        # Agrupar liquidaciones por año (usando el queryset sin paginar)
        liquidaciones_por_anio = {}
        for liquidacion in todas_liquidaciones:
            anio = liquidacion.anio
            if anio not in liquidaciones_por_anio:
                liquidaciones_por_anio[anio] = []
            liquidaciones_por_anio[anio].append(liquidacion)

        context['liquidaciones_por_anio'] = dict(sorted(liquidaciones_por_anio.items(), reverse=True))

        # Estadísticas del funcionario (usando el queryset sin paginar)
        total_liquidaciones = todas_liquidaciones.count()
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
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

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

        # Redirigir a vista segura
        return redirect('admin_liquidaciones_overview')

class AdminEliminarTodasLiquidacionesView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para que administradores eliminen TODAS las liquidaciones del sistema"""

    def test_func(self):
        return self.request.user.role == 'ADMIN'

    def post(self, request):
        confirmacion = request.POST.get('confirmacion', '')
        if confirmacion != 'ELIMINAR TODO':
            messages.error(request, 'Frase de confirmación de seguridad incorrecta. No se eliminaron las liquidaciones.')
            return redirect('admin_liquidaciones_overview')

        liquidaciones = Liquidacion.objects.all()
        count = 0
        for liq in liquidaciones:
            if liq.archivo:
                liq.archivo.delete(save=False)
            liq.delete()
            count += 1
            
        messages.success(request, f'Se eliminaron totalmente {count} liquidaciones del sistema.')
        return redirect('admin_liquidaciones_overview')


class AdminDescargarLiquidacionesFuncionarioView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para que administradores descarguen las liquidaciones de un funcionário específico por año como ZIP"""

    def test_func(self):
        return self.request.user.role in ['ADMIN', 'SECRETARIA']

    def get(self, request, funcionario_id, anio):
        try:
            funcionario = CustomUser.objects.get(id=funcionario_id)
        except CustomUser.DoesNotExist:
            messages.error(request, 'El funcionário no existe.')
            return redirect('admin_liquidaciones_overview')

        liquidaciones = Liquidacion.objects.filter(
            funcionario_id=funcionario_id,
            anio=anio
        ).order_by('-mes')

        if not liquidaciones:
            messages.warning(request, f'No hay liquidaciones disponibles para el año {anio}.')
            return redirect('admin_funcionario_liquidaciones', funcionario_id=funcionario_id)

        # Crear archivo ZIP en memoria
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for liquidacion in liquidaciones:
                # Leer el archivo PDF
                if liquidacion.archivo:
                    with liquidacion.archivo.open('rb') as pdf_file:
                        pdf_data = pdf_file.read()

                    # Nombre del archivo en el ZIP
                    filename = f"liquidacion_{liquidacion.anio}_{liquidacion.mes:02d}_{funcionario.run}.pdf"
                    zip_file.writestr(filename, pdf_data)

        zip_buffer.seek(0)

        # Crear respuesta HTTP
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename=liquidaciones_{funcionario.run}_{anio}.zip'

        return response

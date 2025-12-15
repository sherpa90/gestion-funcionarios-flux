"""
Servicios de negocio para liquidaciones de sueldo.
Separación de lógica de negocio de las vistas.
"""

import logging
from typing import Optional, List, Tuple
from django.core.files.base import ContentFile
from django.db.models import QuerySet
from .models import Liquidacion
from users.models import CustomUser
from core.utils import normalize_rut, clean_rut_for_matching

logger = logging.getLogger(__name__)


class PayrollService:
    """Servicio para operaciones relacionadas con liquidaciones de sueldo"""

    @staticmethod
    def find_user_by_rut(rut_encontrado: str) -> Optional[CustomUser]:
        """
        Encuentra un usuario por RUT normalizado.

        Args:
            rut_encontrado: RUT extraído del PDF

        Returns:
            Usuario encontrado o None
        """
        try:
            # Normalizar el RUT encontrado
            rut_normalizado = normalize_rut(rut_encontrado)
            rut_para_comparar = clean_rut_for_matching(rut_normalizado)

            # Buscar usuario comparando RUTs limpios
            for user in CustomUser.objects.all():
                user_rut_limpio = clean_rut_for_matching(user.run)
                if user_rut_limpio == rut_para_comparar:
                    return user

            return None

        except Exception as e:
            logger.error(f"Error finding user by RUT {rut_encontrado}: {e}")
            return None

    @staticmethod
    def create_payroll_from_pdf(
        pdf_content: bytes,
        user: CustomUser,
        month: int,
        year: int,
        page_num: int
    ) -> Optional[Liquidacion]:
        """
        Crea una liquidación a partir de contenido PDF.

        Args:
            pdf_content: Contenido del PDF
            user: Usuario al que pertenece la liquidación
            month: Mes de la liquidación
            year: Año de la liquidación
            page_num: Número de página (para logging)

        Returns:
            Liquidacion creada o None si hay error
        """
        try:
            import io
            import pypdf

            # Crear PDF con una sola página
            pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_content))
            pdf_writer = pypdf.PdfWriter()
            pdf_writer.add_page(pdf_reader.pages[page_num])

            output_buffer = io.BytesIO()
            pdf_writer.write(output_buffer)

            # Crear nombre de archivo
            filename = f"liquidacion_{year}_{month}_{user.run}.pdf"

            # Crear liquidación
            liquidacion = Liquidacion(
                funcionario=user,
                mes=month,
                anio=year
            )
            liquidacion.archivo.save(filename, ContentFile(output_buffer.getvalue()))

            logger.info(f"Payroll created: {filename} for user {user.get_full_name()}")
            return liquidacion

        except Exception as e:
            logger.error(f"Error creating payroll for user {user.get_full_name()}, page {page_num}: {e}")
            return None

    @staticmethod
    def get_user_payrolls_by_year(user: CustomUser) -> dict:
        """
        Obtiene las liquidaciones de un usuario agrupadas por año.

        Args:
            user: Usuario

        Returns:
            Dict con años como keys y listas de liquidaciones como values
        """
        liquidaciones = Liquidacion.objects.filter(
            funcionario=user
        ).order_by('-anio', '-mes')

        liquidaciones_por_anio = {}
        for liquidacion in liquidaciones:
            anio = liquidacion.anio
            if anio not in liquidaciones_por_anio:
                liquidaciones_por_anio[anio] = []
            liquidaciones_por_anio[anio].append(liquidacion)

        return dict(sorted(liquidaciones_por_anio.items(), reverse=True))

    @staticmethod
    def get_payroll_statistics(user: CustomUser) -> dict:
        """
        Calcula estadísticas de liquidaciones para un usuario.

        Args:
            user: Usuario

        Returns:
            Dict con estadísticas
        """
        liquidaciones = Liquidacion.objects.filter(funcionario=user)
        total_liquidaciones = liquidaciones.count()
        anios_con_liquidaciones = liquidaciones.values_list('anio', flat=True).distinct().count()

        return {
            'total_liquidaciones': total_liquidaciones,
            'anios_con_liquidaciones': anios_con_liquidaciones,
            'promedio_por_anio': round(total_liquidaciones / anios_con_liquidaciones, 1) if anios_con_liquidaciones > 0 else 0
        }


class PayrollValidationService:
    """Servicio para validaciones relacionadas con liquidaciones"""

    @staticmethod
    def validate_month_year(month: int, year: int) -> Tuple[bool, str]:
        """
        Valida mes y año para liquidaciones.

        Args:
            month: Mes (1-12)
            year: Año

        Returns:
            Tuple (is_valid, error_message)
        """
        if not (1 <= month <= 12):
            return False, "El mes debe estar entre 1 y 12"

        current_year = 2025  # Podría obtenerse dinámicamente
        if not (2020 <= year <= current_year + 1):
            return False, f"El año debe estar entre 2020 y {current_year + 1}"

        return True, ""

    @staticmethod
    def can_upload_payroll(user: CustomUser, target_user: CustomUser, month: int, year: int) -> Tuple[bool, str]:
        """
        Verifica si un usuario puede subir una liquidación.

        Args:
            user: Usuario que intenta subir
            target_user: Usuario objetivo de la liquidación
            month: Mes
            year: Año

        Returns:
            Tuple (can_upload, error_message)
        """
        # Solo admin/secretaria pueden subir liquidaciones
        allowed_roles = ['ADMIN', 'SECRETARIA']
        if user.role not in allowed_roles:
            return False, "No tienes permisos para subir liquidaciones"

        # Verificar que no exista ya una liquidación para ese mes/año
        existing = Liquidacion.objects.filter(
            funcionario=target_user,
            mes=month,
            anio=year
        ).exists()

        if existing:
            return False, f"Ya existe una liquidación para {month}/{year} de {target_user.get_full_name()}"

        return True, ""
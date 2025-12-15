import os
import tempfile
from django.test import TestCase
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from .models import Liquidacion

User = get_user_model()


class LiquidacionModelTest(TestCase):
    """Test básico para el modelo Liquidacion"""

    def setUp(self):
        """Crear datos de prueba"""
        self.user = User.objects.create_user(
            run='12345678-9',
            username='12345678-9',
            first_name='Juan',
            last_name='Pérez',
            email='juan.perez@test.cl'
        )

    def test_liquidacion_creation(self):
        """Test que se puede crear una liquidación"""
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n')
            temp_path = tmp_file.name

        try:
            with open(temp_path, 'rb') as f:
                file_content = f.read()

            liquidacion = Liquidacion.objects.create(
                funcionario=self.user,
                mes=12,
                anio=2024,
                archivo=ContentFile(file_content, name='test.pdf')
            )

            self.assertEqual(liquidacion.funcionario, self.user)
            self.assertEqual(liquidacion.mes, 12)
            self.assertEqual(liquidacion.anio, 2024)
            self.assertIsNotNone(liquidacion.archivo)
            self.assertEqual(str(liquidacion), f"Liquidación 12/2024 - {self.user.get_full_name()} ({self.user.run})")

        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_liquidacion_ordering(self):
        """Test que el ordering funciona correctamente"""
        # Crear múltiples liquidaciones
        liquidaciones_data = [
            (1, 2024),  # Enero 2024
            (12, 2024), # Diciembre 2024
            (6, 2023),  # Junio 2023
        ]

        for mes, anio in liquidaciones_data:
            Liquidacion.objects.create(
                funcionario=self.user,
                mes=mes,
                anio=anio,
                archivo=ContentFile(b'test', name=f'test_{mes}_{anio}.pdf')
            )

        # Verificar ordering (primero por año descendente, luego mes descendente)
        liquidaciones = Liquidacion.objects.filter(funcionario=self.user)
        ordered = list(liquidaciones)

        # Debería ser: Diciembre 2024, Enero 2024, Junio 2023
        self.assertEqual(ordered[0].anio, 2024)
        self.assertEqual(ordered[0].mes, 12)
        self.assertEqual(ordered[1].anio, 2024)
        self.assertEqual(ordered[1].mes, 1)
        self.assertEqual(ordered[2].anio, 2023)
        self.assertEqual(ordered[2].mes, 6)


class PayrollUploadTest(TestCase):
    """Test básico para la carga de liquidaciones"""

    def setUp(self):
        self.user = User.objects.create_user(
            run='12345678-9',
            username='12345678-9',
            first_name='Juan',
            last_name='Pérez',
            email='juan.perez@test.cl'
        )

    def test_rut_normalization(self):
        """Test que la normalización de RUT funciona"""
        from core.utils import normalize_rut

        test_cases = [
            ('12345678-9', '12.345.678-9'),
            ('12.345.678-9', '12.345.678-9'),
            ('12 345 678-9', '12.345.678-9'),
            ('123456789', '12.345.678-9'),
        ]

        for input_rut, expected in test_cases:
            with self.subTest(input_rut=input_rut):
                result = normalize_rut(input_rut)
                self.assertEqual(result, expected)
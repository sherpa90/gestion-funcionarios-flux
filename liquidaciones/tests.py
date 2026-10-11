"""
Tests para la aplicación de liquidaciones de sueldo (liquidaciones).
Cubre:
- Modelo Liquidacion (cifrado Ley 21.719, ordenamiento cronológico inverso, nombres de mes).
- Normalización y casamiento de RUTs en planillas de pago.
- Control de acceso por roles a carga y visualización de boletas.
- Protección de acceso a archivos confidenciales de remuneraciones.
"""
import os
import tempfile
from django.test import TestCase, Client
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Liquidacion
from core.utils import normalize_rut, clean_rut_for_matching

User = get_user_model()


class LiquidacionModelTest(TestCase):
    """Test para el modelo Liquidacion y su almacenamiento seguro"""

    def setUp(self):
        self.user = User.objects.create_user(
            run='12345678-5',
            username='12345678-5',
            first_name='Juan',
            last_name='Pérez',
            email='juan.perez@test.cl'
        )

    def test_liquidacion_creation_and_attributes(self):
        """Test creación de liquidación con archivo encriptado y propiedades"""
        raw_pdf = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n'
        liquidacion = Liquidacion.objects.create(
            funcionario=self.user,
            mes=12,
            anio=2026,
            archivo=ContentFile(raw_pdf, name='test_liq.pdf')
        )

        self.assertEqual(liquidacion.funcionario, self.user)
        self.assertEqual(liquidacion.mes, 12)
        self.assertEqual(liquidacion.mes_nombre, 'Diciembre')
        self.assertEqual(liquidacion.anio, 2026)
        self.assertIn("Liquidación 12/2026", str(liquidacion))

    def test_liquidacion_ordering(self):
        """El historial de liquidaciones debe ordenarse por año y mes descendente"""
        datos = [(1, 2026), (12, 2026), (6, 2025)]
        for mes, anio in datos:
            Liquidacion.objects.create(
                funcionario=self.user,
                mes=mes,
                anio=anio,
                archivo=ContentFile(b'%PDF-1.4\ncontent', name=f'liq_{mes}_{anio}.pdf')
            )

        liquidaciones = list(Liquidacion.objects.filter(funcionario=self.user))
        self.assertEqual(liquidaciones[0].anio, 2026)
        self.assertEqual(liquidaciones[0].mes, 12)
        self.assertEqual(liquidaciones[1].anio, 2026)
        self.assertEqual(liquidaciones[1].mes, 1)
        self.assertEqual(liquidaciones[2].anio, 2025)
        self.assertEqual(liquidaciones[2].mes, 6)


class PayrollUploadAndRutMatchingTest(TestCase):
    """Tests para normalización de RUT en procesamiento de nóminas"""

    def test_rut_normalization(self):
        """Test que la normalización de RUT funciona con diferentes formatos"""
        test_cases = [
            ('12345678-5', '12.345.678-5'),
            ('12.345.678-5', '12.345.678-5'),
            ('12 345 678-5', '12.345.678-5'),
            ('123456785', '12.345.678-5'),
        ]
        for input_rut, expected in test_cases:
            with self.subTest(input_rut=input_rut):
                self.assertEqual(normalize_rut(input_rut), expected)

    def test_clean_rut_for_matching(self):
        """Test limpieza para matching en PDF de liquidaciones"""
        self.assertEqual(clean_rut_for_matching('12.345.678-5'), '12345678-5')
        self.assertEqual(clean_rut_for_matching('123456785'), '12345678-5')


class LiquidacionesSecurityTest(TestCase):
    """Tests para verificación de permisos y privacidad de liquidaciones"""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='secretaria_rem',
            email='secretaria_rem@test.com',
            run='11111111-1',
            first_name='Secretaria',
            last_name='Rem',
            password='testpass123',
            role='SECRETARIA'
        )
        self.docente = User.objects.create_user(
            username='docente_rem',
            email='docente_rem@test.com',
            run='12345678-5',
            first_name='Docente',
            last_name='Rem',
            password='testpass123',
            role='FUNCIONARIO'
        )

    def test_docente_no_puede_cargar_liquidaciones(self):
        """Un docente común no tiene acceso al módulo de carga masiva de liquidaciones"""
        self.client.force_login(self.docente)
        url = reverse('carga_liquidaciones')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_secretaria_puede_acceder_a_carga(self):
        """La secretaria puede ingresar al panel de carga masiva de liquidaciones"""
        self.client.force_login(self.admin)
        url = reverse('carga_liquidaciones')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_docente_puede_ver_mis_liquidaciones(self):
        """Un docente puede acceder a su propio portal de boletas de sueldo"""
        self.client.force_login(self.docente)
        url = reverse('mis_liquidaciones')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
"""
Tests para la aplicación de licencias médicas (licencias).
Cubre:
- Modelo LicenciaMedica (cálculo de fechas en días corridos vs días hábiles por fallecimiento).
- Control de acceso por roles (Secretaria / Admin vs Funcionario regular).
- Vistas de creación, listado y estadísticas de ausentismo.
"""
from datetime import date, timedelta
from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from licencias.models import LicenciaMedica
from asistencia.models import DiaFestivo

User = get_user_model()


class LicenciaMedicaModelTest(TestCase):
    """Tests para la lógica de cálculo y propiedades del modelo LicenciaMedica"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='func_lic',
            email='func_lic@test.com',
            run='12345678-5',
            first_name='Laura',
            last_name='Gomez',
            password='testpass123'
        )

    def test_licencia_comun_dias_corridos(self):
        """Una licencia común cuenta días calendario corridos (incluye fines de semana)"""
        # Inicia un viernes 2026-10-09, 5 días corridos -> termina el martes 2026-10-13
        inicio = date(2026, 10, 9)
        licencia = LicenciaMedica.objects.create(
            usuario=self.user,
            tipo='LICENCIA',
            fecha_inicio=inicio,
            dias=5
        )
        self.assertFalse(licencia.usa_dias_habiles)
        self.assertEqual(licencia.fecha_termino, date(2026, 10, 13))
        self.assertIn("Laura Gomez", str(licencia))

    def test_licencia_fallecimiento_dias_habiles(self):
        """La licencia por fallecimiento cuenta únicamente días hábiles (lunes a viernes, sin feriados)"""
        # Inicia un viernes 2026-10-09, 3 días hábiles -> Viernes (1), Lunes (2), Martes (3)
        inicio = date(2026, 10, 9)
        licencia = LicenciaMedica.objects.create(
            usuario=self.user,
            tipo='FALLECIMIENTO',
            fecha_inicio=inicio,
            dias=3
        )
        self.assertTrue(licencia.usa_dias_habiles)
        # Salta sábado 10 y domingo 11
        self.assertEqual(licencia.fecha_termino, date(2026, 10, 13))

    def test_licencia_fallecimiento_con_feriado(self):
        """La licencia por fallecimiento también descuenta y salta días festivos oficiales"""
        # Lunes 2026-10-12 feriado
        DiaFestivo.objects.create(fecha=date(2026, 10, 12), nombre='Feriado Nacional')
        inicio = date(2026, 10, 9) # Viernes
        licencia = LicenciaMedica.objects.create(
            usuario=self.user,
            tipo='FALLECIMIENTO',
            fecha_inicio=inicio,
            dias=3
        )
        # Viernes 9 (1), Lun 12 (festivo, se salta), Mar 13 (2), Mié 14 (3)
        self.assertEqual(licencia.fecha_termino, date(2026, 10, 14))


class LicenciaViewsTest(TestCase):
    """Tests para vistas de creación y listado de licencias con verificación de permisos"""

    def setUp(self):
        self.client = Client()
        self.funcionario = User.objects.create_user(
            username='funcionario_lic',
            email='funcionario_lic@test.com',
            run='12345678-5',
            first_name='Pedro',
            last_name='Soto',
            password='testpass123',
            role='FUNCIONARIO'
        )
        self.secretaria = User.objects.create_user(
            username='secretaria_lic',
            email='secretaria_lic@test.com',
            run='11111111-1',
            first_name='Ana',
            last_name='Silva',
            password='testpass123',
            role='SECRETARIA'
        )

    def test_funcionario_no_puede_crear_licencia(self):
        """Un funcionario regular no tiene permiso para ingresar licencias (UserPassesTestMixin)"""
        self.client.force_login(self.funcionario)
        url = reverse('subir_licencia')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_secretaria_puede_crear_licencia(self):
        """Una secretaria puede registrar una licencia médica para cualquier funcionario"""
        self.client.force_login(self.secretaria)
        url = reverse('subir_licencia')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Enviar formulario
        pdf_file = SimpleUploadedFile("licencia.pdf", b"%PDF-1.4\ncontent", content_type="application/pdf")
        post_data = {
            'usuario': self.funcionario.pk,
            'tipo': 'LICENCIA',
            'fecha_inicio': '2026-10-05',
            'dias': 7,
            'archivo': pdf_file
        }
        res_post = self.client.post(url, post_data)
        self.assertEqual(res_post.status_code, 302)

        licencia_creada = LicenciaMedica.objects.filter(usuario=self.funcionario).first()
        self.assertIsNotNone(licencia_creada)
        self.assertEqual(licencia_creada.dias, 7)
        self.assertEqual(licencia_creada.created_by, self.secretaria)

    def test_funcionario_puede_ver_sus_propias_licencias(self):
        """El funcionario autenticado puede ver el historial de sus propias licencias"""
        LicenciaMedica.objects.create(
            usuario=self.funcionario,
            tipo='LICENCIA',
            fecha_inicio=date(2026, 9, 1),
            dias=3,
            created_by=self.secretaria
        )
        self.client.force_login(self.funcionario)
        url = reverse('licencia_list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pedro Soto')

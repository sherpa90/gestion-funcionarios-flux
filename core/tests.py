"""
Tests para la aplicación base (core):
- Validadores de RUN (Módulo 11) y archivos (magic bytes).
- Utilidades de RUT (clean_rut_for_matching, normalize_rut).
- BusinessDayCalculator (cálculo de días hábiles, exclusión de feriados y soporte a SERENOS).
- EncryptedFileSystemStorage (cifrado en reposo Ley 21.719).
- Middleware de seguridad (SecurityHeadersMiddleware).
- Endpoint de monitoreo /health/.
"""
import io
import tempfile
import os
from datetime import date
from django.test import TestCase, RequestFactory
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.http import HttpResponse

from core.validators import validate_run, validate_file_upload
from core.utils import clean_rut_for_matching, normalize_rut
from core.services import BusinessDayCalculator
from core.storage import EncryptedFileSystemStorage
from core.security import SecurityHeadersMiddleware
from core.views import HealthCheckView
from asistencia.models import DiaFestivo

User = get_user_model()


class RunValidatorAndUtilsTest(TestCase):
    """Tests para validación y formateo de RUN chileno"""

    def test_clean_rut_for_matching(self):
        """Test limpieza de RUT quitando puntos pero conservando guión"""
        self.assertEqual(clean_rut_for_matching('12.345.678-5'), '12345678-5')
        self.assertEqual(clean_rut_for_matching(' 12 345 678-5 '), '12345678-5')
        self.assertEqual(clean_rut_for_matching('123456785'), '12345678-5')
        self.assertEqual(clean_rut_for_matching(''), '')

    def test_normalize_rut(self):
        """Test formateo chileno estándar con puntos y guión"""
        self.assertEqual(normalize_rut('123456785'), '12.345.678-5')
        self.assertEqual(normalize_rut('12345678-5'), '12.345.678-5')
        self.assertEqual(normalize_rut('12.345.678-5'), '12.345.678-5')
        self.assertEqual(normalize_rut('12345674'), '1.234.567-4')

    def test_validate_run_valid(self):
        """Verificar RUTs válidos con DV numérico y con K"""
        valid_runs = ['12.345.678-5', '11.111.111-1', '12345670-K', '1234567-4', '7654321-6']
        for r in valid_runs:
            try:
                validate_run(r)
            except ValidationError:
                self.fail(f"RUT {r} debería ser válido según Módulo 11")

    def test_validate_run_invalid(self):
        """Verificar que RUTs con DV alterado o formato inválido lanzan ValidationError"""
        invalid_runs = ['12.345.678-9', '11.111.111-2', '12345670-5', 'XYZ-1', '']
        for r in invalid_runs:
            with self.assertRaises(ValidationError):
                validate_run(r)


class FileUploadValidatorTest(TestCase):
    """Tests para validación de tipo y magic bytes de archivos subidos"""

    def test_valid_pdf_file(self):
        """Un PDF con encabezado %PDF válido debe ser aceptado"""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n"
        upload = SimpleUploadedFile("document.pdf", pdf_content, content_type="application/pdf")
        try:
            validate_file_upload(upload)
        except ValidationError as e:
            self.fail(f"PDF válido fue rechazado: {e}")

    def test_disallowed_extension(self):
        """Archivos con extensiones no permitidas (.exe, .sh) deben ser rechazados"""
        exe_file = SimpleUploadedFile("script.sh", b"#!/bin/bash\necho hi", content_type="text/plain")
        with self.assertRaises(ValidationError):
            validate_file_upload(exe_file)

    def test_tampered_magic_bytes(self):
        """Un archivo de texto renombrado a .pdf debe ser rechazado por discrepancia en magic bytes"""
        fake_pdf = SimpleUploadedFile("fake.pdf", b"This is plain text pretending to be PDF", content_type="application/pdf")
        with self.assertRaises(ValidationError):
            validate_file_upload(fake_pdf)


class BusinessDayCalculatorTest(TestCase):
    """Tests para el servicio de cálculo de días hábiles y plazos"""

    def setUp(self):
        self.sereno = User.objects.create_user(
            username='sereno_calc',
            email='sereno_calc@test.com',
            run='11111111-1',
            first_name='Sereno',
            last_name='Calc',
            password='testpass123',
            funcion='SERENO'
        )

    def test_business_day_regular(self):
        """Lunes a viernes son hábiles, fines de semana son inhábiles para funcionarios comunes"""
        lunes = date(2026, 10, 5)   # Lunes
        sabado = date(2026, 10, 10) # Sábado
        domingo = date(2026, 10, 11) # Domingo

        self.assertTrue(BusinessDayCalculator.is_business_day(lunes))
        self.assertFalse(BusinessDayCalculator.is_business_day(sabado))
        self.assertFalse(BusinessDayCalculator.is_business_day(domingo))

    def test_business_day_sereno(self):
        """Para SERENOS, los fines de semana cuentan como días hábiles"""
        sabado = date(2026, 10, 10)
        domingo = date(2026, 10, 11)

        self.assertTrue(BusinessDayCalculator.is_business_day(sabado, user=self.sereno))
        self.assertTrue(BusinessDayCalculator.is_business_day(domingo, user=self.sereno))

    def test_business_day_with_festivo(self):
        """Los feriados registrados en DiaFestivo no son hábiles"""
        festivo_date = date(2026, 10, 12)  # Lunes
        DiaFestivo.objects.create(fecha=festivo_date, nombre='Encuentro de Dos Mundos')

        self.assertFalse(BusinessDayCalculator.is_business_day(festivo_date))

    def test_calculate_end_date_half_day(self):
        """Duración de medio día (0.5) retorna la misma fecha de inicio"""
        inicio = date(2026, 10, 5) # Lunes
        fin = BusinessDayCalculator.calculate_end_date(inicio, 0.5)
        self.assertEqual(fin, inicio)

    def test_calculate_end_date_skipping_weekend(self):
        """Solicitar 2 días comenzando un viernes termina el lunes siguiente"""
        viernes = date(2026, 10, 9)
        fin = BusinessDayCalculator.calculate_end_date(viernes, 2)
        esperado = date(2026, 10, 12) # Lunes
        self.assertEqual(fin, esperado)

    def test_count_business_days(self):
        """Contar días hábiles entre lunes y viernes de una misma semana = 5"""
        lunes = date(2026, 10, 5)
        viernes = date(2026, 10, 9)
        self.assertEqual(BusinessDayCalculator.count_business_days(lunes, viernes), 5)


class EncryptedStorageTest(TestCase):
    """Tests para EncryptedFileSystemStorage (Cifrado en reposo)"""

    def test_encrypt_and_decrypt_cycle(self):
        """Guardar un archivo lo encripta en disco y open() lo desencripta en memoria"""
        storage = EncryptedFileSystemStorage()
        raw_content = b"Informacion confidencial de personal escolar"
        filename = "test_encrypted.txt"

        saved_name = storage.save(filename, ContentFile(raw_content))
        try:
            # En el disco físico debe estar cifrado (no debe coincidir con el texto original)
            disk_path = storage.path(saved_name)
            with open(disk_path, 'rb') as f:
                disk_bytes = f.read()
            self.assertNotEqual(disk_bytes, raw_content)

            # Al leerlo a través del storage se desencripta automáticamente
            with storage.open(saved_name, 'rb') as f:
                decrypted_bytes = f.read()
            self.assertEqual(decrypted_bytes, raw_content)
        finally:
            if storage.exists(saved_name):
                storage.delete(saved_name)


class SecurityAndMonitoringTest(TestCase):
    """Tests para SecurityHeadersMiddleware y HealthCheckView"""

    def setUp(self):
        self.factory = RequestFactory()

    def test_security_headers_middleware(self):
        """El middleware debe agregar encabezados de seguridad OWASP"""
        request = self.factory.get('/')
        middleware = SecurityHeadersMiddleware(lambda r: HttpResponse("OK"))
        response = middleware(request)

        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response['X-Frame-Options'], 'DENY')
        self.assertIn('strict-origin', response['Referrer-Policy'])
        self.assertIn('geolocation=()', response['Permissions-Policy'])

    def test_health_check_endpoint(self):
        """El endpoint de salud debe responder status 200 y JSON con estado 'healthy'"""
        request = self.factory.get('/health/')
        view = HealthCheckView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'"status": "healthy"', response.content)

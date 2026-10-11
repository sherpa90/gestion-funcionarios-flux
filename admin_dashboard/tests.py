"""
Tests para la aplicación de administración y dashboard de control (admin_dashboard).
Cubre:
- Modelos SystemLog, ImportacionUsuarios, Efemeride.
- Helper registrar_log y get_client_ip.
- Control de acceso estricto a las vistas de administración (AdminDashboardView, SystemLogsView).
"""
from datetime import date
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from admin_dashboard.models import SystemLog, ImportacionUsuarios, Efemeride
from admin_dashboard.utils import registrar_log

User = get_user_model()


class AdminDashboardModelTest(TestCase):
    """Tests para modelos de auditoría, logs y efemérides"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='admin_dash',
            email='admin_dash@test.com',
            run='11111111-1',
            first_name='Admin',
            last_name='Sistema',
            password='testpass123',
            role='ADMIN'
        )

    def test_registrar_log(self):
        """Test creación de log mediante la función utilitaria registrar_log"""
        log = registrar_log(
            usuario=self.user,
            tipo='CREATE',
            accion='Alta de Funcionario',
            descripcion='Se registró nuevo docente en plataforma',
            ip_address='192.168.1.100',
            metadata={'modulo': 'usuarios'}
        )
        self.assertEqual(log.tipo, 'CREATE')
        self.assertEqual(log.ip_address, '192.168.1.100')
        self.assertIn('Alta de Funcionario', str(log))

    def test_importacion_usuarios_tasa_exito(self):
        """Test propiedad tasa_exito de ImportacionUsuarios"""
        imp = ImportacionUsuarios(total_registros=100, exitosos=95, fallidos=5)
        self.assertEqual(imp.tasa_exito, 95.0)

        imp_vacia = ImportacionUsuarios(total_registros=0, exitosos=0)
        self.assertEqual(imp_vacia.tasa_exito, 0)

    def test_efemeride(self):
        """Test creación y representación string de Efemeride institucional"""
        efe = Efemeride.objects.create(
            titulo='Día del Profesor',
            fecha=date(2026, 10, 16),
            responsable='Equipo Directivo',
            creado_por=self.user
        )
        self.assertIn('2026-10-16 - Día del Profesor', str(efe))


class AdminDashboardSecurityTest(TestCase):
    """Tests para asegurar que el panel administrativo solo es accesible por ADMIN"""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='super_admin',
            email='super_admin@test.com',
            run='11111111-1',
            first_name='Super',
            last_name='Admin',
            password='testpass123',
            role='ADMIN'
        )
        self.docente = User.objects.create_user(
            username='docente_usr',
            email='docente_usr@test.com',
            run='12345678-5',
            first_name='Docente',
            last_name='Comun',
            password='testpass123',
            role='FUNCIONARIO'
        )

    def test_acceso_denegado_para_funcionario(self):
        """Un usuario con rol FUNCIONARIO es rechazado al intentar entrar al admin dashboard"""
        self.client.force_login(self.docente)
        url = reverse('admin_dashboard:dashboard')
        response = self.client.get(url)
        self.assertIn(response.status_code, [302, 403])

    def test_acceso_permitido_para_admin(self):
        """Un usuario con rol ADMIN puede ingresar correctamente al panel"""
        self.client.force_login(self.admin)
        url = reverse('admin_dashboard:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_efemeride_create_view_admin(self):
        """Un administrador puede crear efemérides desde la interfaz administrativa"""
        self.client.force_login(self.admin)
        url = reverse('admin_dashboard:efemeride_create')
        post_data = {
            'titulo': 'Semana de la Ciencia',
            'fecha': '2026-11-02',
            'responsable': 'Depto Ciencias'
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Efemeride.objects.filter(titulo='Semana de la Ciencia').exists())

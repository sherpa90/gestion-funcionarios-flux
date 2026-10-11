"""
Tests completos para la aplicación de usuarios (users).
Cubre modelos, managers, validadores, cálculo de categorías y saldos de días.
"""
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.validators import validate_run
from users.models import BajaPeriodo, GrupoCorreo, DirectorioTelefonico
from asistencia.models import HorarioFuncionario, DiaHorario

User = get_user_model()


class CustomUserModelTest(TestCase):
    """Tests para el modelo CustomUser y CustomUserManager"""
    
    def test_crear_usuario_basico(self):
        """Test crear usuario con campos mínimos y valores por defecto"""
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            run='12345678-5',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
        self.assertEqual(user.email, 'test@test.com')
        self.assertEqual(user.username, 'testuser')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.role, 'FUNCIONARIO')
        self.assertEqual(user.dias_disponibles, 6.0)
        # Verifica que se crea automáticamente el HorarioFuncionario por defecto
        self.assertTrue(HorarioFuncionario.objects.filter(funcionario=user).exists())
    
    def test_crear_superuser(self):
        """Test crear superusuario con CustomUserManager garantizando role ADMIN"""
        user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            run='12345678-5',
            first_name='Admin',
            last_name='User',
            password='adminpass123'
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, 'ADMIN')
    
    def test_usuario_con_rol_funcionario(self):
        """Test crear usuario con rol FUNCIONARIO"""
        user = User.objects.create_user(
            username='funcionario',
            email='func@test.com',
            run='11111111-1',
            first_name='Funcionario',
            last_name='Test',
            password='funcpass123',
            role='FUNCIONARIO'
        )
        self.assertEqual(user.role, 'FUNCIONARIO')
    
    def test_usuario_con_rol_director(self):
        """Test crear usuario con rol DIRECTOR"""
        user = User.objects.create_user(
            username='director',
            email='director@test.com',
            run='11111111-1',
            first_name='Director',
            last_name='Test',
            password='dirpass123',
            role='DIRECTOR'
        )
        self.assertEqual(user.role, 'DIRECTOR')
    
    def test_get_full_name(self):
        """Test nombre completo del usuario"""
        user = User(
            first_name='Marcelo',
            last_name='Rosas'
        )
        self.assertEqual(user.get_full_name(), 'Marcelo Rosas')

    def test_run_normalization_on_save(self):
        """Test que el RUN se normaliza con puntos y guion al guardar"""
        user = User.objects.create_user(
            username='normuser',
            email='norm@test.com',
            run='123456785',
            first_name='Norm',
            last_name='User',
            password='testpass123'
        )
        self.assertEqual(user.run, '12.345.678-5')

    def test_categoria_funcionario(self):
        """Test para verificar la clasificación por categorías (DOCENTE, ASISTENTE, ADMINISTRATIVO)"""
        # Administrativo por rol
        admin = User(role='ADMIN', first_name='A', last_name='A')
        self.assertEqual(admin.categoria_funcionario, 'ADMINISTRATIVO')
        
        director = User(role='DIRECTOR', first_name='D', last_name='D')
        self.assertEqual(director.categoria_funcionario, 'ADMINISTRATIVO')
        
        # Docente
        docente = User(role='FUNCIONARIO', tipo_funcionario='DOCENTE', first_name='Doc', last_name='T')
        self.assertEqual(docente.categoria_funcionario, 'DOCENTE')
        
        docente_funcion = User(role='FUNCIONARIO', funcion='DOCENTE_AULA', first_name='Doc', last_name='T')
        self.assertEqual(docente_funcion.categoria_funcionario, 'DOCENTE')

        # Asistente
        asistente = User(role='FUNCIONARIO', tipo_funcionario='ASISTENTE', first_name='Asis', last_name='T')
        self.assertEqual(asistente.categoria_funcionario, 'ASISTENTE')

        sereno = User(role='FUNCIONARIO', funcion='SERENO', first_name='Ser', last_name='T')
        self.assertEqual(sereno.categoria_funcionario, 'ASISTENTE')

    def test_dias_disponibles_pct(self):
        """Test cálculo de porcentaje de días disponibles"""
        user = User(dias_disponibles=6.0)
        self.assertEqual(user.dias_disponibles_pct, 100.0)

        user.dias_disponibles = 3.0
        self.assertEqual(user.dias_disponibles_pct, 50.0)

        user.dias_disponibles = 0.0
        self.assertEqual(user.dias_disponibles_pct, 0.0)

    def test_is_on_baja_on_date(self):
        """Test verificación de baja global y por BajaPeriodo"""
        user = User.objects.create_user(
            username='bajausr',
            email='baja@test.com',
            run='11111111-1',
            first_name='Baja',
            last_name='Test',
            password='testpass123'
        )
        hoy = timezone.now().date()
        
        # Inicialmente no está de baja
        self.assertFalse(user.is_on_baja_on_date(hoy))

        # Crear BajaPeriodo ACTIVO
        BajaPeriodo.objects.create(
            usuario=user,
            motivo='Licencia',
            fecha_inicio=hoy - timedelta(days=2),
            fecha_termino=hoy + timedelta(days=2),
            estado='ACTIVO'
        )
        self.assertTrue(user.is_on_baja_on_date(hoy))
        self.assertFalse(user.is_on_baja_on_date(hoy + timedelta(days=5)))

    def test_es_dia_activo(self):
        """Test determinación de día hábil activo para funcionario y sereno"""
        user = User.objects.create_user(
            username='regular',
            email='regular@test.com',
            run='12345678-5',
            first_name='Regular',
            last_name='User',
            password='testpass123'
        )
        # Lunes 2026-10-05 (weekday = 0)
        lunes = date(2026, 10, 5)
        # Sábado 2026-10-10 (weekday = 5)
        sabado = date(2026, 10, 10)
        
        self.assertTrue(user.es_dia_activo(lunes))
        self.assertFalse(user.es_dia_activo(sabado))


class ValidatorsTest(TestCase):
    """Tests para validadores de RUN chileno"""
    
    def test_validate_run_correcto(self):
        """Test RUTs matemáticamente válidos (Módulo 11)"""
        valid_ruts = [
            '12345678-5',
            '11.111.111-1',
            '11111111-1',
            '1234567-4',
            '7654321-6',
            '12345670-K',
            '12.345.670-k',
        ]
        for rut in valid_ruts:
            try:
                validate_run(rut)
            except ValidationError:
                self.fail(f'RUT {rut} debería ser válido')
    
    def test_validate_run_incorrecto(self):
        """Test RUTs inválidos"""
        invalid_ruts = [
            '12345678',      # Sin guion/DV
            'ABCD-1',        # Letras en cuerpo
            '',              # Vacío
            '12345678-K',    # DV incorrecto (debería ser 5)
            '11111111-2',    # DV incorrecto (debería ser 1)
            '1234567-8',     # DV incorrecto (debería ser 4)
        ]
        for rut in invalid_ruts:
            with self.assertRaises(ValidationError):
                validate_run(rut)


class ModulosAuxiliaresUserTest(TestCase):
    """Tests para GrupoCorreo y DirectorioTelefonico"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='admin_aux',
            email='admin_aux@test.com',
            run='11111111-1',
            first_name='Admin',
            last_name='Aux',
            password='testpass123',
            role='ADMIN'
        )

    def test_grupo_correo(self):
        """Test creación y cantidad de miembros de GrupoCorreo"""
        grupo = GrupoCorreo.objects.create(
            nombre='Docentes Media',
            correo='docentes.media@colegio.cl',
            descripcion='Grupo de profesores de educación media',
            creado_por=self.user
        )
        grupo.miembros.add(self.user)
        self.assertEqual(grupo.cantidad_miembros, 1)
        self.assertIn('Docentes Media', str(grupo))

    def test_directorio_telefonico(self):
        """Test creación de anexo en DirectorioTelefonico"""
        directorio = DirectorioTelefonico.objects.create(
            lugar='Dirección',
            anexo='101',
            descripcion='Oficina de Dirección',
            creado_por=self.user
        )
        self.assertEqual(str(directorio), 'Dirección - 101')


class UserListViewTest(TestCase):
    """Test para la vista UserListView (/usuarios/)"""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin_list',
            email='admin_list@test.com',
            run='11111111-1',
            first_name='Admin',
            last_name='List',
            password='adminpass123',
            role='ADMIN'
        )

    def test_user_list_view_get(self):
        """Verifica que /usuarios/ carga correctamente sin errores de select_related"""
        self.client.force_login(self.admin)
        from django.urls import reverse
        response = self.client.get(reverse('user_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin List')


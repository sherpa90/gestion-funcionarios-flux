"""
Tests básicos para la aplicación de usuarios.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from core.validators import validate_run

User = get_user_model()


class CustomUserModelTest(TestCase):
    """Tests para el modelo de usuario"""
    
    def test_crear_usuario_basico(self):
        """Test crear usuario con campos mínimos"""
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
    
    def test_crear_superuser(self):
        """Test crear superusuario"""
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
            run='22222222-2',
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


class ValidatorsTest(TestCase):
    """Tests para validadores"""
    
    def test_validate_run_correcto(self):
        """Test RUT válido"""
        # RUTs válidos
        valid_ruts = ['12345678-5', '1234567-8', '7654321-0']
        for rut in valid_ruts:
            try:
                validate_run(rut)
            except ValidationError:
                self.fail(f'RUT {rut} debería ser válido')
    
    def test_validate_run_incorrecto(self):
        """Test RUT inválido"""
        # RUTs inválidos
        invalid_ruts = ['12345678', 'ABCD-1', '']
        for rut in invalid_ruts:
            with self.assertRaises(ValidationError):
                validate_run(rut)

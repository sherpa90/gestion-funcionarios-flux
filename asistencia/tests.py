"""
Tests básicos para la aplicación de asistencia.
"""
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from users.models import CustomUser
from asistencia.models import (
    HorarioFuncionario, 
    RegistroAsistencia, 
    DiaFestivo
)


class HorarioFuncionarioTest(TestCase):
    """Tests para el modelo de horario"""
    
    def setUp(self):
        """Crear usuario de prueba"""
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@test.com',
            run='12345678-5',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
    
    def test_crear_horario(self):
        """Test crear horario de funcionario"""
        horario = HorarioFuncionario.objects.create(
            funcionario=self.user,
            hora_entrada=timezone.datetime.strptime('08:00:00', '%H:%M:%S').time(),
            tolerancia_minutos=15,
            activo=True
        )
        self.assertEqual(horario.funcionario, self.user)
        self.assertEqual(horario.hora_entrada.hour, 8)
        self.assertTrue(horario.activo)
    
    def test_horario_str(self):
        """Test string representation del horario"""
        horario = HorarioFuncionario.objects.create(
            funcionario=self.user,
            hora_entrada=timezone.datetime.strptime('08:00:00', '%H:%M:%S').time()
        )
        self.assertIn('Test User', str(horario))
        self.assertIn('08:00:00', str(horario))


class RegistroAsistenciaTest(TestCase):
    """Tests para el modelo de registro de asistencia"""
    
    def setUp(self):
        """Crear datos de prueba"""
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@test.com',
            run='12345678-5',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
        self.horario = HorarioFuncionario.objects.create(
            functorio=self.user,
            hora_entrada=timezone.datetime.strptime('08:00:00', '%H:%M:%S').time(),
            tolerancia_minutos=15
        )
    
    def test_crear_registro_asistencia(self):
        """Test crear registro de asistencia"""
        fecha = timezone.now().date()
        registro = RegistroAsistencia.objects.create(
            functorio=self.user,
            fecha=fecha,
            hora_entrada_real=timezone.datetime.strptime('08:00:00', '%H:%M:%S').time(),
            horario_asignado=self.horario
        )
        self.assertEqual(registro.funcionario, self.user)
        self.assertEqual(registro.fecha, fecha)
    
    def test_calcular_retraso_puntual(self):
        """Test retraso cuando llega puntual"""
        registro = RegistroAsistencia.objects.create(
            functorio=self.user,
            fecha=timezone.now().date(),
            hora_entrada_real=timezone.datetime.strptime('08:10:00', '%H:%M:%S').time(),  # 8:10
            horario_asignado=self.horario  # 8:00 con 15 min tolerancia
        )
        # Llega a las 8:10, tolerancia 15 min = no hay retraso
        self.assertEqual(registro.calcular_retraso(), 0)
    
    def test_calcular_retraso_tarde(self):
        """Test retraso cuando llega tarde"""
        registro = RegistroAsistencia.objects.create(
            functorio=self.user,
            fecha=timezone.now().date(),
            hora_entrada_real=timezone.datetime.strptime('08:30:00', '%H:%M:%S').time(),  # 8:30
            horario_asignado=self.horario  # 8:00 con 15 min tolerancia
        )
        # Llega a las 8:30, retraso = 30 - 15 = 15 min
        self.assertEqual(registro.calcular_retraso(), 15)
    
    def test_calcular_tiempo_trabajado(self):
        """Test cálculo de tiempo trabajado"""
        registro = RegistroAsistencia.objects.create(
            functorio=self.user,
            fecha=timezone.now().date(),
            hora_entrada_real=timezone.datetime.strptime('08:00:00', '%H:%M:%S').time(),
            hora_salida_real=timezone.datetime.strptime('17:00:00', '%H:%M:%S').time(),
            horario_asignado=self.horario
        )
        # 8:00 a 17:00 = 9 horas = 540 minutos
        self.assertEqual(registro.calcular_tiempo_trabajado(), 540)


class DiaFestivoTest(TestCase):
    """Tests para el modelo de días festivos"""
    
    def test_crear_dia_festivo(self):
        """Test crear día festivo"""
        fecha = timezone.now().date() + timedelta(days=30)  # Futuro
        festivo = DiaFestivo.objects.create(
            fecha=fecha,
            nombre='Navidad',
            descripcion='Celebración de Navidad'
        )
        self.assertEqual(festivo.nombre, 'Navidad')
        self.assertEqual(str(festivo), f'{fecha} - Navidad')
    
    def test_es_dia_festivo(self):
        """Test verificar si es día festivo"""
        fecha = timezone.now().date() + timedelta(days=30)
        DiaFestivo.objects.create(fecha=fecha, nombre='Test')
        
        self.assertTrue(DiaFestivo.es_dia_festivo(fecha))
        self.assertFalse(DiaFestivo.es_dia_festivo(fecha - timedelta(days=1)))

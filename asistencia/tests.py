"""
Tests básicos para la aplicación de asistencia.
"""
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta, time, date
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
        HorarioFuncionario.objects.filter(funcionario=self.user).delete()
    
    def test_crear_horario(self):
        """Test crear horario de funcionario"""
        horario = HorarioFuncionario.objects.create(
            funcionario=self.user,
            hora_entrada=timezone.datetime.strptime('08:00:00', '%H:%M:%S').time(),
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
        # Obtener o actualizar el horario existente
        self.horario, _ = HorarioFuncionario.objects.get_or_create(
            funcionario=self.user,
            defaults={'hora_entrada': timezone.datetime.strptime('08:00:00', '%H:%M:%S').time()}
        )
        self.horario.hora_entrada = timezone.datetime.strptime('08:00:00', '%H:%M:%S').time()
        self.horario.save()
    
    def test_crear_registro_asistencia(self):
        """Test crear registro de asistencia"""
        fecha = timezone.now().date()
        registro = RegistroAsistencia.objects.create(
            funcionario=self.user,
            fecha=fecha,
            hora_entrada_real=timezone.datetime.strptime('08:00:00', '%H:%M:%S').time(),
            horario_asignado=self.horario
        )
        self.assertEqual(registro.funcionario, self.user)
        self.assertEqual(registro.fecha, fecha)
    
    def test_calcular_retraso_puntual(self):
        """Test retraso cuando llega puntual"""
        registro = RegistroAsistencia.objects.create(
            funcionario=self.user,
            fecha=timezone.now().date(),
            hora_entrada_real=timezone.datetime.strptime('08:10:00', '%H:%M:%S').time(),  # 8:10
            horario_asignado=self.horario  # 8:00 sin tolerancia
        )
        # Llega a las 8:10, sin tolerancia = 10 min retraso
        self.assertEqual(registro.calcular_retraso(), 10)
    
    def test_calcular_retraso_tarde(self):
        """Test retraso cuando llega tarde"""
        registro = RegistroAsistencia.objects.create(
            funcionario=self.user,
            fecha=timezone.now().date(),
            hora_entrada_real=timezone.datetime.strptime('08:30:00', '%H:%M:%S').time(),  # 8:30
            horario_asignado=self.horario  # 8:00 sin tolerancia
        )
        # Llega a las 8:30, sin tolerancia = 30 min retraso
        self.assertEqual(registro.calcular_retraso(), 30)
    
    def test_calcular_tiempo_trabajado(self):
        """Test cálculo de tiempo trabajado"""
        registro = RegistroAsistencia.objects.create(
            funcionario=self.user,
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


class SerenoAsistenciaTest(TestCase):
    """Tests para el control de turnos y asistencia de serenos"""
    
    def setUp(self):
        self.sereno = CustomUser.objects.create_user(
            username='serenotest',
            email='sereno@test.com',
            run='18765432-1',
            first_name='Sereno',
            last_name='Test',
            password='testpass123',
            funcion='SERENO'
        )
        # Limpiar horario automático
        HorarioFuncionario.objects.filter(funcionario=self.sereno).delete()
        
        # Crear horario con turnos rotativos para el sereno
        self.horario = HorarioFuncionario.objects.create(
            funcionario=self.sereno,
            hora_entrada=time(20, 0), # entrada general
            activo=True
        )
        
        # DiaHorario para Lunes (0) en Semana 1 (T1) -> Entrada 20:00, Salida 08:00 (siguiente día)
        from asistencia.models import DiaHorario
        self.dia_t1 = DiaHorario.objects.create(
            horario=self.horario,
            dia_semana=0,
            semana_tipo=1,
            hora_entrada=time(20, 0),
            hora_salida=time(8, 0),
            activo=True
        )
        
        # DiaHorario para Lunes (0) en Semana 2 (T2) -> Entrada 22:00, Salida 06:00
        self.dia_t2 = DiaHorario.objects.create(
            horario=self.horario,
            dia_semana=0,
            semana_tipo=2,
            hora_entrada=time(22, 0),
            hora_salida=time(6, 0),
            activo=True
        )

    def test_get_semana_tipo_sereno(self):
        """Test que get_semana_tipo retorna la asignación del sereno o la paridad por defecto"""
        from asistencia.models import DiaHorario, SemanaAsignadaSereno
        # 2026-07-20 es Lunes de la semana ISO 30 (Par)
        fecha_lunes = date(2026, 7, 20)
        
        # Por defecto (sin asignación explícita): debe retornar 2 (par)
        self.assertEqual(DiaHorario.get_semana_tipo(fecha_lunes, self.sereno), 2)
        
        # Asignar explícitamente Turno 1 (semana_tipo=1) para la semana 30
        SemanaAsignadaSereno.objects.create(
            funcionario=self.sereno,
            anio=2026,
            semana_iso=30,
            turno=1
        )
        
        # Ahora debe retornar 1 (Turno 1)
        self.assertEqual(DiaHorario.get_semana_tipo(fecha_lunes, self.sereno), 1)

    def test_asistencia_sereno_atraso(self):
        """Test cálculo de retraso para serenos basado en su turno semanal asignado"""
        from asistencia.models import SemanaAsignadaSereno
        # 2026-07-20 (semana 30)
        fecha = date(2026, 7, 20)
        
        # Asignar Turno 1 (Entrada: 20:00)
        SemanaAsignadaSereno.objects.create(
            funcionario=self.sereno,
            anio=2026,
            semana_iso=30,
            turno=1
        )
        
        # Caso 1: Llega puntual a las 19:55
        registro_puntual = RegistroAsistencia.objects.create(
            funcionario=self.sereno,
            fecha=fecha,
            hora_entrada_real=time(19, 55),
            horario_asignado=self.horario
        )
        self.assertEqual(registro_puntual.calcular_retraso(), 0)
        self.assertEqual(registro_puntual.estado, 'PUNTUAL')
        
        # Caso 2: Llega tarde a las 20:15 (15 minutos de retraso)
        registro_puntual.delete()
        registro_tarde = RegistroAsistencia.objects.create(
            funcionario=self.sereno,
            fecha=fecha,
            hora_entrada_real=time(20, 15),
            horario_asignado=self.horario
        )
        self.assertEqual(registro_tarde.calcular_retraso(), 15)
        self.assertEqual(registro_tarde.estado, 'RETRASO')

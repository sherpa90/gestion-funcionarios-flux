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
    DiaFestivo,
    DiaHorario
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


class AlegacionAsistenciaTest(TestCase):
    """Tests para el flujo de alegaciones y justificaciones sobre registros de asistencia"""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='func_aleg',
            email='func_aleg@test.com',
            run='12345678-5',
            first_name='Funcionario',
            last_name='Aleg',
            password='testpass123'
        )
        self.admin = CustomUser.objects.create_user(
            username='admin_aleg',
            email='admin_aleg@test.com',
            run='11111111-1',
            first_name='Admin',
            last_name='Aleg',
            password='testpass123',
            role='ADMIN'
        )
        self.horario = HorarioFuncionario.objects.filter(funcionario=self.user).first()
        self.registro = RegistroAsistencia.objects.create(
            funcionario=self.user,
            fecha=date(2026, 10, 5),
            horario_asignado=self.horario,
            estado='RETRASO',
            minutos_retraso=25
        )

    def test_crear_y_revisar_alegacion(self):
        """Un funcionario crea una alegación y un administrador la revisa y aprueba"""
        from asistencia.models import AlegacionAsistencia
        alegacion = AlegacionAsistencia.objects.create(
            registro_asistencia=self.registro,
            motivo='Corte imprevisto en la vía pública',
            estado='PENDIENTE'
        )
        self.assertEqual(alegacion.estado, 'PENDIENTE')
        self.assertTrue(alegacion.puede_revisar(self.admin))
        self.assertFalse(alegacion.puede_revisar(self.user))

        # Admin aprueba
        alegacion.estado = 'APROBADA'
        alegacion.respuesta_admin = 'Comprobado y justificado'
        alegacion.revisado_por = self.admin
        alegacion.fecha_revision = timezone.now()
        alegacion.save()

        self.assertEqual(alegacion.estado, 'APROBADA')
        self.assertEqual(alegacion.revisado_por, self.admin)


class HorarioExcepcionalTest(TestCase):
    """Tests para horarios excepcionales (actos escolares, salidas tempranas)"""

    def setUp(self):
        self.docente = CustomUser.objects.create_user(
            username='docente_exc',
            email='docente_exc@test.com',
            run='12345678-5',
            first_name='Docente',
            last_name='Exc',
            password='testpass123',
            role='FUNCIONARIO',
            tipo_funcionario='DOCENTE'
        )
        self.sereno = CustomUser.objects.create_user(
            username='sereno_exc',
            email='sereno_exc@test.com',
            run='11111111-1',
            first_name='Sereno',
            last_name='Exc',
            password='testpass123',
            role='FUNCIONARIO',
            funcion='SERENO'
        )

    def test_horario_excepcional_aplica_a_grupos(self):
        """Verificar filtro de aplicación: TODOS, SERENOS o FUNCIONARIOS"""
        from asistencia.models import HorarioExcepcional
        fecha = date(2026, 10, 8)

        # Excepcional solo para funcionarios (no serenos)
        exc_func = HorarioExcepcional(fecha=fecha, motivo='Capacitación', aplica_a='FUNCIONARIOS')
        self.assertTrue(exc_func.aplica_a_funcionario(self.docente))
        self.assertFalse(exc_func.aplica_a_funcionario(self.sereno))

        # Excepcional solo para serenos
        exc_sereno = HorarioExcepcional(fecha=fecha, motivo='Ronda especial', aplica_a='SERENOS')
        self.assertFalse(exc_sereno.aplica_a_funcionario(self.docente))
        self.assertTrue(exc_sereno.aplica_a_funcionario(self.sereno))


class VigenciaHistoricaHorarioTest(TestCase):
    """
    Tests de la solución estructural:
    Garantiza que un cambio de horario (entrada o salida) rige solo desde el día del cambio
    en adelante y no altera las métricas, retrasos ni estados pasados bajo ningún punto de vista.
    """

    def setUp(self):
        from datetime import time, timedelta
        self.hoy = timezone.localdate()
        self.user = CustomUser.objects.create_user(
            username='funcionario_historico',
            email='func_hist@test.com',
            run='15555555-5',
            first_name='Carlos',
            last_name='Historico',
            password='testpass123',
            role='FUNCIONARIO',
            date_joined=timezone.now() - timedelta(days=30)
        )
        self.admin = CustomUser.objects.create_user(
            username='admin_horarios',
            email='admin_h@test.com',
            run='16666666-6',
            first_name='Admin',
            last_name='Horarios',
            password='testpass123',
            role='ADMIN'
        )

        # Eliminar cualquier horario por defecto y crear el inicial vigente desde hace 20 días
        HorarioFuncionario.objects.filter(funcionario=self.user).delete()
        self.horario_inicial = HorarioFuncionario.objects.create(
            funcionario=self.user,
            hora_entrada=time(8, 0),
            fecha_desde=self.hoy - timedelta(days=20),
            activo=True
        )
        # Configurar todos los días 08:00 a 17:00
        for dia in range(7):
            DiaHorario.objects.create(
                horario=self.horario_inicial,
                dia_semana=dia,
                hora_entrada=time(8, 0),
                hora_salida=time(17, 0),
                activo=True
            )

    def test_cambio_horario_no_afecta_metricas_pasadas(self):
        """
        Un funcionario que llegó a las 08:15 hace 5 días tuvo 15 min de retraso (horario 08:00).
        Si hoy su horario se cambia a las 08:30, el registro pasado NO debe cambiar a PUNTUAL
        ni perder sus 15 minutos de retraso.
        """
        from datetime import time, timedelta
        from django.test import Client
        import json

        fecha_pasada = self.hoy - timedelta(days=5)
        # Registro histórico: llegó a las 08:15 (retraso de 15 min respecto a las 08:00)
        reg_pasado = RegistroAsistencia.objects.create(
            funcionario=self.user,
            fecha=fecha_pasada,
            hora_entrada_real=time(8, 15),
            hora_salida_real=time(17, 0),
            horario_asignado=self.horario_inicial
        )
        self.assertEqual(reg_pasado.minutos_retraso, 15)
        self.assertEqual(reg_pasado.estado, 'RETRASO')
        self.assertEqual(reg_pasado.hora_entrada_teorica, time(8, 0))

        # El administrador cambia el horario semanal hoy: nueva entrada 08:30
        client = Client()
        client.force_login(self.admin)

        dias_nuevo_horario = []
        for dia in range(7):
            dias_nuevo_horario.append({
                'dia_semana': dia,
                'activo': True,
                'hora_entrada': '08:30',
                'hora_salida': '17:30',
                'semana_tipo': ''
            })

        response = client.post(
            f'/asistencia/horario/guardar-semanal/{self.user.id}/',
            data=json.dumps({'dias': dias_nuevo_horario, 'total_minutos': 40 * 60}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        # 1. Verificar que el horario anterior fue cerrado y se creó uno nuevo
        self.horario_inicial.refresh_from_db()
        self.assertEqual(self.horario_inicial.fecha_hasta, self.hoy - timedelta(days=1))

        horario_nuevo = self.user.horario
        self.assertNotEqual(horario_nuevo.id, self.horario_inicial.id)
        self.assertEqual(horario_nuevo.fecha_desde, self.hoy)
        self.assertIsNone(horario_nuevo.fecha_hasta)

        # 2. VERIFICACIÓN CRÍTICA: El registro pasado NO fue alterado
        reg_pasado.refresh_from_db()
        self.assertEqual(reg_pasado.horario_asignado_id, self.horario_inicial.id)
        self.assertEqual(reg_pasado.minutos_retraso, 15, "El retraso histórico no debe cambiar bajo ningún punto de vista")
        self.assertEqual(reg_pasado.estado, 'RETRASO', "El estado histórico debe mantenerse en RETRASO")
        self.assertEqual(reg_pasado.hora_entrada_teorica, time(8, 0), "La hora teórica histórica debe mantenerse en 08:00")

        # 3. Un registro de hoy con la misma hora real (08:15) ahora es PUNTUAL con el nuevo horario (08:30)
        reg_hoy = RegistroAsistencia.objects.create(
            funcionario=self.user,
            fecha=self.hoy,
            hora_entrada_real=time(8, 15),
            hora_salida_real=time(17, 30)
        )
        self.assertEqual(reg_hoy.horario_asignado_id, horario_nuevo.id)
        self.assertEqual(reg_hoy.minutos_retraso, 0)
        self.assertEqual(reg_hoy.estado, 'PUNTUAL')
        self.assertEqual(reg_hoy.hora_entrada_teorica, time(8, 30))

    def test_consulta_horario_por_fecha(self):
        """Verifica que get_horario_para_fecha retorne la versión correcta según el día"""
        from datetime import time, timedelta

        fecha_ayer = self.hoy - timedelta(days=1)
        self.horario_inicial.fecha_hasta = fecha_ayer
        self.horario_inicial.save()

        horario_v2 = HorarioFuncionario.objects.create(
            funcionario=self.user,
            hora_entrada=time(9, 0),
            fecha_desde=self.hoy,
            activo=True
        )

        # Fecha previa al cambio retorna horario_inicial
        self.assertEqual(self.user.get_horario_para_fecha(fecha_ayer).id, self.horario_inicial.id)
        # Fecha de hoy retorna horario_v2
        self.assertEqual(self.user.get_horario_para_fecha(self.hoy).id, horario_v2.id)

    def test_cambio_horario_con_fecha_especifica_futura(self):
        """Verifica que guardar_horario_semanal con fecha_desde específica rija exactamente desde esa fecha"""
        from datetime import time, timedelta
        from django.urls import reverse
        import json

        self.client.force_login(self.admin)
        fecha_futura = self.hoy + timedelta(days=7)

        dias_payload = [
            {'dia_semana': 0, 'activo': True, 'hora_entrada': '09:00', 'hora_salida': '18:00', 'semana_tipo': None},
            {'dia_semana': 1, 'activo': True, 'hora_entrada': '09:00', 'hora_salida': '18:00', 'semana_tipo': None},
        ]

        response = self.client.post(
            reverse('asistencia:guardar_horario_semanal', kwargs={'user_id': self.user.id}),
            data=json.dumps({
                'dias': dias_payload,
                'total_minutos': 1080,
                'fecha_desde': fecha_futura.strftime('%Y-%m-%d')
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        # El horario anterior debe quedar cerrado el día antes de la fecha futura
        self.horario_inicial.refresh_from_db()
        self.assertEqual(self.horario_inicial.fecha_hasta, fecha_futura - timedelta(days=1))

        # El nuevo horario debe tener fecha_desde == fecha_futura
        horario_nuevo = HorarioFuncionario.objects.filter(funcionario=self.user, fecha_desde=fecha_futura).first()
        self.assertIsNotNone(horario_nuevo)
        self.assertEqual(horario_nuevo.fecha_desde, fecha_futura)
        self.assertIsNone(horario_nuevo.fecha_hasta)

    def test_cambio_horario_backdating_con_horario_posterior_activo(self):
        """
        Caso: el horario actual tiene fecha_desde POSTERIOR a la fecha_vigencia deseada.
        Ej: horario vigente desde 2026-10-05, pero el admin quiere aplicar un nuevo
        horario desde 2026-10-01. El horario del 05 debe desactivarse para que
        get_horario_para_fecha devuelva el nuevo retroactivo y los registros entre
        el 01 y el 05 se recalculen correctamente.
        """
        from datetime import time, timedelta, date
        from django.test import Client
        from django.urls import reverse
        import json

        # Preparar: el horario inicial tiene fecha_desde = hoy - 5 días (posterior a vigencia)
        # Reemplazamos el setUp con un horario más "reciente"
        HorarioFuncionario.objects.filter(funcionario=self.user).delete()
        RegistroAsistencia.objects.filter(funcionario=self.user).delete()

        fecha_horario_actual = self.hoy - timedelta(days=5)
        horario_reciente = HorarioFuncionario.objects.create(
            funcionario=self.user,
            hora_entrada=time(8, 0),
            fecha_desde=fecha_horario_actual,
            activo=True
        )
        for dia in range(7):
            DiaHorario.objects.create(
                horario=horario_reciente,
                dia_semana=dia,
                hora_entrada=time(8, 0),
                hora_salida=time(17, 0),
                activo=True
            )

        # Registro el día -3: llegó a las 07:50 (puntual con horario 08:00)
        fecha_registro = self.hoy - timedelta(days=3)
        reg = RegistroAsistencia.objects.create(
            funcionario=self.user,
            fecha=fecha_registro,
            hora_entrada_real=time(7, 50),
            hora_salida_real=time(17, 0),
            horario_asignado=horario_reciente
        )
        self.assertEqual(reg.estado, 'PUNTUAL')
        self.assertEqual(reg.minutos_retraso, 0)

        # El admin cambia el horario con fecha_vigencia = hoy - 7 (anterior al horario activo)
        fecha_vigencia = self.hoy - timedelta(days=7)
        self.assertTrue(horario_reciente.fecha_desde > fecha_vigencia,
                        "El horario activo debe tener fecha_desde > fecha_vigencia para activar el else")

        client = Client()
        client.force_login(self.admin)

        dias_nuevo_horario = [
            {'dia_semana': dia, 'activo': True, 'hora_entrada': '07:45',
             'hora_salida': '16:00', 'semana_tipo': ''}
            for dia in range(7)
        ]
        response = client.post(
            reverse('asistencia:guardar_horario_semanal', kwargs={'user_id': self.user.id}),
            data=json.dumps({
                'dias': dias_nuevo_horario,
                'total_minutos': 40 * 60,
                'fecha_desde': fecha_vigencia.strftime('%Y-%m-%d')
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        # 1. El horario reciente debe haberse desactivado (activo=False)
        horario_reciente.refresh_from_db()
        self.assertFalse(horario_reciente.activo,
                         "El horario posterior debe desactivarse al crear uno retroactivo")

        # 2. El nuevo horario debe tener fecha_desde == fecha_vigencia y activo=True
        horario_nuevo = HorarioFuncionario.objects.filter(
            funcionario=self.user, activo=True
        ).first()
        self.assertIsNotNone(horario_nuevo)
        self.assertEqual(horario_nuevo.fecha_desde, fecha_vigencia)
        self.assertEqual(horario_nuevo.hora_entrada, time(7, 45))

        # 3. El registro (llegó 07:50) ahora DEBE ser RETRASO con el nuevo horario 07:45
        reg.refresh_from_db()
        self.assertEqual(reg.horario_asignado_id, horario_nuevo.id)
        self.assertEqual(reg.hora_entrada_teorica, time(7, 45))
        self.assertEqual(reg.minutos_retraso, 5,
                         "5 minutos de retraso: llegó 07:50 y el horario nuevo es 07:45")
        self.assertEqual(reg.estado, 'RETRASO',
                         "Debe marcarse RETRASO, no PUNTUAL")

        # 4. get_horario_para_fecha para la fecha del registro debe devolver el nuevo horario
        horario_para_fecha = self.user.get_horario_para_fecha(fecha_registro)
        self.assertEqual(horario_para_fecha.id, horario_nuevo.id,
                         "get_horario_para_fecha debe devolver el nuevo horario retroactivo")




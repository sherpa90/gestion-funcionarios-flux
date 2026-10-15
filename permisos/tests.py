"""
Tests completos para la aplicación de permisos (permisos).
Cubre modelos, reglas de negocio de saldos, aprobaciones, rechazos,
cancelaciones con devolución de días, y vistas de workflow.
"""
from datetime import timedelta, date
from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from permisos.models import SolicitudPermiso
from asistencia.models import RegistroAsistencia, HorarioFuncionario

User = get_user_model()


class SolicitudPermisoModelTest(TestCase):
    """Tests para el modelo SolicitudPermiso y sus métodos"""
    
    def setUp(self):
        """Crear datos de prueba"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            run='12345678-5',
            first_name='Test',
            last_name='User',
            password='testpass123',
            dias_disponibles=6.0
        )
        self.user_director = User.objects.create_user(
            username='director',
            email='director@test.com',
            run='11111111-1',
            first_name='Director',
            last_name='Test',
            password='dirpass123',
            role='DIRECTOR'
        )
    
    def test_crear_solicitud_permiso(self):
        """Test crear solicitud de permiso con campos válidos"""
        fecha_inicio = timezone.now().date() + timedelta(days=5)
        fecha_termino = fecha_inicio + timedelta(days=2)
        
        solicitud = SolicitudPermiso.objects.create(
            usuario=self.user,
            fecha_inicio=fecha_inicio,
            fecha_termino=fecha_termino,
            dias_solicitados=1.0,
            jornada='FD',
            observacion='Asuntos personales',
            estado='PENDIENTE'
        )
        
        self.assertEqual(solicitud.usuario, self.user)
        self.assertEqual(solicitud.estado, 'PENDIENTE')
        self.assertEqual(solicitud.dias_solicitados, 1.0)
        self.assertEqual(solicitud.jornada, 'FD')
        self.assertEqual(solicitud.observacion, 'Asuntos personales')
        self.assertIn(str(fecha_inicio), str(solicitud))

    def test_es_fuera_de_plazo(self):
        """Test propiedad es_fuera_de_plazo cuando la anticipación es menor a 2 días"""
        hoy = timezone.now().date()
        # Solicitud para mañana (< 2 días)
        solicitud_urgente = SolicitudPermiso(
            usuario=self.user,
            fecha_inicio=hoy + timedelta(days=1),
            dias_solicitados=1.0
        )
        self.assertTrue(solicitud_urgente.es_fuera_de_plazo)

        # Solicitud con 5 días de anticipación (>= 2 días)
        solicitud_a_tiempo = SolicitudPermiso(
            usuario=self.user,
            fecha_inicio=hoy + timedelta(days=5),
            dias_solicitados=1.0
        )
        self.assertFalse(solicitud_a_tiempo.es_fuera_de_plazo)

    def test_sincronizacion_asistencia_al_aprobar(self):
        """Test que al guardar un permiso en APROBADO se reevalúan los registros de asistencia"""
        fecha = timezone.now().date() + timedelta(days=7)
        horario = HorarioFuncionario.objects.filter(funcionario=self.user).first()
        
        registro = RegistroAsistencia.objects.create(
            funcionario=self.user,
            fecha=fecha,
            horario_asignado=horario,
            estado='AUSENTE'
        )
        
        # Crear y aprobar permiso para esa fecha
        solicitud = SolicitudPermiso.objects.create(
            usuario=self.user,
            fecha_inicio=fecha,
            fecha_termino=fecha,
            dias_solicitados=1.0,
            jornada='FD',
            estado='APROBADO'
        )
        
        registro.refresh_from_db()
        self.assertEqual(registro.estado, 'DIA_ADMINISTRATIVO')


class SolicitudActionWorkflowTest(TestCase):
    """Tests para el flujo de aprobación, rechazo y cancelación de permisos"""

    def setUp(self):
        self.client = Client()
        self.funcionario = User.objects.create_user(
            username='func_perm',
            email='func_perm@test.com',
            run='12345678-5',
            first_name='Juan',
            last_name='Perez',
            password='testpass123',
            dias_disponibles=6.0,
            role='FUNCIONARIO'
        )
        self.director = User.objects.create_user(
            username='dir_perm',
            email='dir_perm@test.com',
            run='11111111-1',
            first_name='Directora',
            last_name='Maria',
            password='dirpass123',
            role='DIRECTOR'
        )
        self.fecha = timezone.now().date() + timedelta(days=5)
        self.solicitud = SolicitudPermiso.objects.create(
            usuario=self.funcionario,
            fecha_inicio=self.fecha,
            fecha_termino=self.fecha,
            dias_solicitados=1.0,
            jornada='FD',
            observacion='Trámite notarial',
            estado='PENDIENTE'
        )

    def test_aprobar_solicitud_descuenta_dias(self):
        """Test que la aprobación de un permiso por Director descuenta saldo de días"""
        self.client.force_login(self.director)
        url = reverse('solicitud_action', kwargs={'pk': self.solicitud.pk, 'action': 'approve'})
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        self.solicitud.refresh_from_db()
        self.funcionario.refresh_from_db()

        self.assertEqual(self.solicitud.estado, 'APROBADO')
        self.assertEqual(self.solicitud.aprobado_por, self.director)
        self.assertEqual(self.funcionario.dias_disponibles, 5.0)  # 6.0 - 1.0 = 5.0

    def test_rechazar_solicitud(self):
        """Test que el rechazo de un permiso registra el motivo y no descuenta saldo"""
        self.client.force_login(self.director)
        url = reverse('solicitud_action', kwargs={'pk': self.solicitud.pk, 'action': 'reject'})
        
        response = self.client.post(url, {'motivo_rechazo': 'Actividad institucional inaplazable'})
        self.assertEqual(response.status_code, 302)

        self.solicitud.refresh_from_db()
        self.funcionario.refresh_from_db()

        self.assertEqual(self.solicitud.estado, 'RECHAZADO')
        self.assertEqual(self.solicitud.motivo_rechazo, 'Actividad institucional inaplazable')
        self.assertEqual(self.funcionario.dias_disponibles, 6.0)

    def test_cancelar_solicitud_aprobada_devuelve_dias(self):
        """Test que al cancelar una solicitud previamente aprobada se reembolsan los días"""
        self.client.force_login(self.director)
        
        # 1. Aprobar
        url_approve = reverse('solicitud_action', kwargs={'pk': self.solicitud.pk, 'action': 'approve'})
        self.client.post(url_approve)
        self.funcionario.refresh_from_db()
        self.assertEqual(self.funcionario.dias_disponibles, 5.0)

        # 2. Cancelar
        url_cancel = reverse('solicitud_action', kwargs={'pk': self.solicitud.pk, 'action': 'cancel'})
        response = self.client.post(url_cancel, {'motivo_cancelacion': 'Suspensión del trámite'})
        self.assertEqual(response.status_code, 302)

        self.solicitud.refresh_from_db()
        self.funcionario.refresh_from_db()

        self.assertEqual(self.solicitud.estado, 'CANCELADO')
        self.assertEqual(self.solicitud.cancelled_by, self.director)
        # Los días deben ser devueltos:
        self.assertEqual(self.funcionario.dias_disponibles, 6.0)

    def test_funcionario_cancela_su_propia_solicitud_pendiente(self):
        """Test que un funcionario puede cancelar su propia solicitud pendiente"""
        self.client.force_login(self.funcionario)
        url = reverse('solicitud_cancel', kwargs={'pk': self.solicitud.pk})
        
        response = self.client.post(url, {'motivo_cancelacion': 'Ya no necesito el día'})
        self.assertEqual(response.status_code, 302)

        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, 'CANCELADO')
        self.assertEqual(self.solicitud.cancelled_by, self.funcionario)

    def test_funcionario_no_puede_aprobar(self):
        """Test que un funcionario común no tiene permiso para aprobar solicitudes (acceso denegado)"""
        self.client.force_login(self.funcionario)
        url = reverse('solicitud_action', kwargs={'pk': self.solicitud.pk, 'action': 'approve'})
        
        response = self.client.post(url)
        # UserPassesTestMixin devuelve 403 Forbidden cuando el test_func falla
        self.assertEqual(response.status_code, 403)

    def test_enviar_resumen_dias_administrativos_fecha_es(self):
        """Test que el comando enviar_resumen_dias_administrativos formatea la fecha en español"""
        from django.core.management import call_command
        from django.core import mail
        import io

        out = io.StringIO()
        mail.outbox = []
        call_command('enviar_resumen_dias_administrativos', force=True, email='director_test@test.com', stdout=out)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['director_test@test.com'])
        
        dias_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        meses_es = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        
        # Debe contener alguno de los nombres de día y mes en español
        html = email.extra_headers.get('html_message', '') or getattr(email, 'html_message', '') or ''
        # send_mail passes html_message in alternatives or extra_headers
        if not html and hasattr(email, 'alternatives'):
            for content, mimetype in email.alternatives:
                if mimetype == 'text/html':
                    html = content
                    break

        self.assertTrue(any(dia in html for dia in dias_es))
        self.assertTrue(any(mes in html for mes in meses_es))


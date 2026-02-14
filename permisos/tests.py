"""
Tests básicos para la aplicación de permisos.
"""
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from users.models import CustomUser
from permisos.models import SolicitudPermiso


class SolicitudPermisoTest(TestCase):
    """Tests para el modelo de solicitudes de permiso"""
    
    def setUp(self):
        """Crear datos de prueba"""
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@test.com',
            run='12345678-5',
            first_name='Test',
            last_name='User',
            password='testpass123',
            dias_disponibles=10
        )
        
        self.user_director = CustomUser.objects.create_user(
            username='director',
            email='director@test.com',
            run='87654321-0',
            first_name='Director',
            last_name='Test',
            password='dirpass123',
            role='DIRECTOR'
        )
    
    def test_crear_solicitud_permiso(self):
        """Test crear solicitud de permiso"""
        fecha_inicio = timezone.now().date() + timedelta(days=5)
        fecha_termino = fecha_inicio + timedelta(days=2)
        
        solicitud = SolicitudPermiso.objects.create(
            usuario=self.user,
            tipo_permiso='DIA_ADMINISTRATIVO',
            fecha_inicio=fecha_inicio,
            fecha_termino=fecha_termino,
            motivo='Asuntos personales',
            dias_solicitados=3,
            estado='PENDIENTE'
        )
        
        self.assertEqual(solicitud.usuario, self.user)
        self.assertEqual(solicitud.estado, 'PENDIENTE')
        self.assertEqual(solicitud.dias_solicitados, 3)
    
    def test_solicitud_aprobada(self):
        """Test aprobar solicitud"""
        solicitud = SolicitudPermiso.objects.create(
            usuario=self.user,
            tipo_permiso='DIA_ADMINISTRATIVO',
            fecha_inicio=timezone.now().date() + timedelta(days=5),
            fecha_termino=timezone.now().date() + timedelta(days=6),
            motivo='Asuntos personales',
            dias_solicitados=2,
            estado='PENDIENTE'
        )
        
        # Aprobar
        solicitud.estado = 'APROBADO'
        solicitud.aprobado_por = self.user_director
        solicitud.save()
        
        self.assertEqual(solicitud.estado, 'APROBADO')
    
    def test_solicitud_rechazada(self):
        """Test rechazar solicitud"""
        solicitud = SolicitudPermiso.objects.create(
            usuario=self.user,
            tipo_permiso='DIA_ADMINISTRATIVO',
            fecha_inicio=timezone.now().date() + timedelta(days=5),
            fecha_termino=timezone.now().date() + timedelta(days=6),
            motivo='Asuntos personales',
            dias_solicitados=2,
            estado='PENDIENTE'
        )
        
        # Rechazar
        solicitud.estado = 'RECHAZADO'
        solicitud.motivo_rechazo = 'Falta de personal'
        solicitud.save()
        
        self.assertEqual(solicitud.estado, 'RECHAZADO')
        self.assertEqual(solicitud.motivo_rechazo, 'Falta de personal')
    
    def test_str_solicitud(self):
        """Test representación string de solicitud"""
        solicitud = SolicitudPermiso.objects.create(
            usuario=self.user,
            tipo_permiso='DIA_ADMINISTRATIVO',
            fecha_inicio=timezone.now().date() + timedelta(days=5),
            fecha_termino=timezone.now().date() + timedelta(days=6),
            motivo='Asuntos personales',
            dias_solicitados=2,
            estado='PENDIENTE'
        )
        
        self.assertIn('Test User', str(solicitud))
        self.assertIn('PENDIENTE', str(solicitud))

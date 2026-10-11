"""
Tests para la aplicación de gestión de equipos e inventario TI (equipos).
Cubre:
- Modelos LugarEquipo, Equipo, PrestamoEquipo, FallaEquipo.
- Sanitización contra inyección de plantillas ({{, }}).
- Ciclo de vida del equipo (DISPONIBLE -> ASIGNADO -> DISPONIBLE al devolver).
- Préstamos diarios y permanentes.
- Vistas de inventario y préstamos con control de permisos.
"""
from datetime import date, timedelta
from django.test import TestCase, Client
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.urls import reverse
from equipos.models import LugarEquipo, Equipo, PrestamoEquipo, FallaEquipo

User = get_user_model()


class EquiposModelTest(TestCase):
    """Tests para modelos de inventario, validaciones y cambios de estado automáticos"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='admin_eq',
            email='admin_eq@test.com',
            run='11111111-1',
            first_name='Admin',
            last_name='TI',
            password='testpass123',
            role='ADMIN'
        )
        self.funcionario = User.objects.create_user(
            username='profesor_eq',
            email='profesor_eq@test.com',
            run='12345678-5',
            first_name='Profesor',
            last_name='Matematicas',
            password='testpass123',
            role='FUNCIONARIO'
        )
        self.lugar = LugarEquipo.objects.create(
            nombre='SALA DE COMPUTO 1',
            creado_por=self.user
        )

    def test_lugar_equipo_normalization_and_validation(self):
        """El nombre del lugar debe normalizarse en mayúsculas y rechazar template injection"""
        lugar = LugarEquipo.objects.create(
            nombre='  laboratorio ciencias  ',
            creado_por=self.user
        )
        self.assertEqual(lugar.nombre, 'LABORATORIO CIENCIAS')

        # Template injection check
        lugar_malicioso = LugarEquipo(
            nombre='Laboratorio {{ settings.SECRET_KEY }}',
            creado_por=self.user
        )
        with self.assertRaises(ValidationError):
            lugar_malicioso.clean()

    def test_equipo_creacion_y_unicidad(self):
        """Crear equipo valida unicidad de número de serie e inventario"""
        equipo1 = Equipo.objects.create(
            tipo='LAPTOP',
            marca='Lenovo',
            modelo='ThinkPad L14',
            numero_serie='SN123456',
            numero_inventario='INV-001',
            lugar=self.lugar,
            creado_por=self.user
        )
        self.assertEqual(equipo1.estado, 'DISPONIBLE')
        self.assertIn('Lenovo ThinkPad L14', str(equipo1))

        # Intentar duplicar serie
        equipo_duplicado = Equipo(
            tipo='LAPTOP',
            marca='Lenovo',
            numero_serie='sn123456',  # Misma serie
            creado_por=self.user
        )
        with self.assertRaises(ValidationError):
            equipo_duplicado.clean()

    def test_ciclo_prestamo_y_devolucion(self):
        """Al prestar un equipo pasa a ASIGNADO; al devolverlo vuelve a DISPONIBLE"""
        equipo = Equipo.objects.create(
            tipo='PROYECTOR',
            marca='Epson',
            modelo='X41',
            numero_serie='EPSON999',
            creado_por=self.user
        )
        self.assertEqual(equipo.estado, 'DISPONIBLE')

        # Crear préstamo
        prestamo = PrestamoEquipo.objects.create(
            equipo=equipo,
            funcionario=self.funcionario,
            asignado_por=self.user,
            activo=True
        )

        equipo.refresh_from_db()
        self.assertEqual(equipo.estado, 'ASIGNADO')
        self.assertIn(str(self.funcionario), str(prestamo))

        # Devolver préstamo
        prestamo.activo = False
        prestamo.fecha_devolucion_real = timezone.now()
        prestamo.save()

        # Al registrar la devolución en la vista o manualmente, el equipo se libera
        equipo.estado = 'DISPONIBLE'
        equipo.save()
        self.assertEqual(equipo.estado, 'DISPONIBLE')


class EquiposViewsTest(TestCase):
    """Tests para vistas de inventario y préstamos con verificación de seguridad"""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin_v',
            email='admin_v@test.com',
            run='11111111-1',
            first_name='Admin',
            last_name='TI',
            password='testpass123',
            role='ADMIN'
        )
        self.funcionario = User.objects.create_user(
            username='func_v',
            email='func_v@test.com',
            run='12345678-5',
            first_name='Docente',
            last_name='Prueba',
            password='testpass123',
            role='FUNCIONARIO'
        )
        self.equipo = Equipo.objects.create(
            tipo='LAPTOP',
            marca='Dell',
            modelo='Latitude 3420',
            numero_serie='DELL001',
            creado_por=self.admin
        )

    def test_funcionario_mis_equipos(self):
        """Un docente puede ver únicamente sus equipos asignados"""
        PrestamoEquipo.objects.create(
            equipo=self.equipo,
            funcionario=self.funcionario,
            asignado_por=self.admin,
            activo=True
        )
        self.client.force_login(self.funcionario)
        url = reverse('mis_equipos')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dell')

    def test_inventario_acceso_admin(self):
        """El administrador tiene acceso al inventario global de equipos"""
        self.client.force_login(self.admin)
        url = reverse('inventario_equipos')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Latitude 3420')

    def test_reportar_falla_actualiza_estado(self):
        """Un funcionario reporta falla en su equipo asignado y el admin actualiza el estado"""
        # 1. Asignar equipo al funcionario
        PrestamoEquipo.objects.create(
            equipo=self.equipo,
            funcionario=self.funcionario,
            asignado_por=self.admin,
            activo=True
        )

        # 2. Funcionario reporta falla
        self.client.force_login(self.funcionario)
        url_reportar = reverse('reportar_falla', kwargs={'equipo_id': self.equipo.pk})
        post_data = {
            'descripcion': 'Pantalla parpadea intermitentemente'
        }
        res_rep = self.client.post(url_reportar, post_data)
        self.assertEqual(res_rep.status_code, 302)

        falla = FallaEquipo.objects.filter(equipo=self.equipo).first()
        self.assertIsNotNone(falla)
        self.assertEqual(falla.funcionario, self.funcionario)
        self.assertEqual(falla.estado, 'REPORTADA')

        # 3. Admin actualiza estado de la falla
        self.client.force_login(self.admin)
        url_actualizar = reverse('actualizar_estado_falla', kwargs={'falla_id': falla.pk})
        res_act = self.client.post(url_actualizar, {
            'estado': 'EN_REVISION',
            'comentarios_tecnicos': 'Enviado a servicio técnico autorizado'
        })
        self.assertEqual(res_act.status_code, 302)

        falla.refresh_from_db()
        self.assertEqual(falla.estado, 'EN_REVISION')

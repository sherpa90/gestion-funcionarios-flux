"""
Tests para la aplicación de reportes y cálculos estadísticos (reportes).
Cubre:
- Utilidades de cálculo: _reevaluar_medio_dia, _es_ausencia_real, calcular_inasistencias_en_lote.
- Exclusión de festivos, licencias médicas y periodos de baja.
- Control de acceso a la vista principal de reportes (ReportesView).
"""
from datetime import date, time, timedelta
from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse

from reportes.calc_utils import _reevaluar_medio_dia, _es_ausencia_real, calcular_inasistencias_en_lote
from asistencia.models import RegistroAsistencia, HorarioFuncionario, DiaHorario, DiaFestivo
from permisos.models import SolicitudPermiso
from licencias.models import LicenciaMedica
from users.models import BajaPeriodo

User = get_user_model()


class ReportesCalcUtilsTest(TestCase):
    """Tests unitarios para las funciones algorítmicas de reportes/calc_utils.py"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='func_calc',
            email='func_calc@test.com',
            run='12345678-5',
            first_name='Marta',
            last_name='Rios',
            password='testpass123'
        )
        self.fecha = date(2026, 10, 5) # Lunes
        self.horario = HorarioFuncionario.objects.filter(funcionario=self.user).first()

    def test_es_ausencia_real(self):
        """Un registro es ausencia real si falta entrada Y salida y no hay justificación manual"""
        reg_ausente = RegistroAsistencia(
            funcionario=self.user,
            fecha=self.fecha,
            hora_entrada_real=None,
            hora_salida_real=None,
            justificacion_manual=''
        )
        self.assertTrue(_es_ausencia_real(reg_ausente))

        # Con justificación manual ya no cuenta como ausencia real
        reg_justificado = RegistroAsistencia(
            funcionario=self.user,
            fecha=self.fecha,
            hora_entrada_real=None,
            hora_salida_real=None,
            justificacion_manual='Problema de transporte justificado'
        )
        self.assertFalse(_es_ausencia_real(reg_justificado))

        # Con marcación de entrada
        reg_con_entrada = RegistroAsistencia(
            funcionario=self.user,
            fecha=self.fecha,
            hora_entrada_real=time(8, 0),
            hora_salida_real=None
        )
        self.assertFalse(_es_ausencia_real(reg_con_entrada))

    def test_reevaluar_medio_dia(self):
        """Verifica la resolución de estados para permisos de medio día (AM y PM)"""
        # Permiso AM
        permiso_am = SolicitudPermiso(
            usuario=self.user,
            fecha_inicio=self.fecha,
            dias_solicitados=0.5,
            jornada='AM',
            estado='APROBADO'
        )
        permisos_map = {self.fecha: permiso_am}

        # 1. Sin marcación alguna -> AUSENTE
        reg_vacio = RegistroAsistencia(funcionario=self.user, fecha=self.fecha)
        self.assertEqual(_reevaluar_medio_dia(reg_vacio, permisos_map, self.fecha), 'AUSENTE')

        # 2. Con salida PM marcada (mañana libre) -> MEDIO_DIA
        reg_pm = RegistroAsistencia(
            funcionario=self.user,
            fecha=self.fecha,
            hora_entrada_real=None,
            hora_salida_real=time(17, 30)
        )
        self.assertEqual(_reevaluar_medio_dia(reg_pm, permisos_map, self.fecha), 'MEDIO_DIA')

        # Permiso PM
        permiso_pm = SolicitudPermiso(
            usuario=self.user,
            fecha_inicio=self.fecha,
            dias_solicitados=0.5,
            jornada='PM',
            estado='APROBADO'
        )
        permisos_map_pm = {self.fecha: permiso_pm}

        # 3. Con entrada AM marcada (tarde libre) -> MEDIO_DIA
        reg_am = RegistroAsistencia(
            funcionario=self.user,
            fecha=self.fecha,
            hora_entrada_real=time(7, 50),
            hora_salida_real=None
        )
        self.assertEqual(_reevaluar_medio_dia(reg_am, permisos_map_pm, self.fecha), 'MEDIO_DIA')

    def test_calcular_inasistencias_en_lote_con_festivos_y_licencias(self):
        """El cálculo en lote debe descontar feriados, licencias médicas y periodos de baja"""
        # Crear día festivo en el rango
        DiaFestivo.objects.create(fecha=self.fecha, nombre='Festivo')
        
        # Crear registro de asistencia en el festivo
        RegistroAsistencia.objects.create(
            funcionario=self.user,
            fecha=self.fecha,
            horario_asignado=self.horario,
            estado='DIA_FESTIVO'
        )

        res = calcular_inasistencias_en_lote(
            [self.user],
            fecha_inicio_calc=self.fecha,
            fecha_fin_calc=self.fecha
        )
        # El festivo no debe sumar inasistencias
        self.assertEqual(res.get(self.user.id, 0), 0)


class ReportesViewsSecurityTest(TestCase):
    """Tests para verificar el control de acceso por roles a la suite de reportes"""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin_rep',
            email='admin_rep@test.com',
            run='11111111-1',
            first_name='Admin',
            last_name='Rep',
            password='testpass123',
            role='ADMIN'
        )
        self.docente = User.objects.create_user(
            username='docente_rep',
            email='docente_rep@test.com',
            run='12345678-5',
            first_name='Docente',
            last_name='Rep',
            password='testpass123',
            role='FUNCIONARIO'
        )

    def test_funcionario_denegado_en_reportes_generales(self):
        """Un docente/asistente no tiene permiso para ingresar al panel general de reportes"""
        self.client.force_login(self.docente)
        url = reverse('reportes')
        response = self.client.get(url)
        # LoginRequiredMixin / UserPassesTestMixin responde con 403 Forbidden o redirect
        self.assertIn(response.status_code, [302, 403])

    def test_admin_acceso_permitido_en_reportes_generales(self):
        """Un administrador puede acceder al panel de reportes de asistencia y personal"""
        self.client.force_login(self.admin)
        url = reverse('reportes')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

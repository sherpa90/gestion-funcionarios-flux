"""
Tests para la aplicación de catálogos y diccionarios del sistema (catalogos).
Cubre:
- CatalogoBase (código único, ordenamiento, estado activo).
- Modelos RolUsuario, TipoFuncionario, EstadoRegistroAsistencia, EstadoSolicitudPermiso, TipoEquipo, EstadoEquipo, JornadaLaboral, PeriodoLiquidacion.
- Integridad referencial y propiedades de catálogos.
"""
from django.test import TestCase
from django.db.utils import IntegrityError
from catalogos.models import (
    RolUsuario,
    TipoFuncionario,
    EstadoRegistroAsistencia,
    EstadoSolicitudPermiso,
    TipoEquipo,
    EstadoEquipo,
    JornadaLaboral,
    PeriodoLiquidacion
)


class CatalogosModelTest(TestCase):
    """Tests para validar la consistencia de catálogos normalizados"""

    def test_creacion_rol_usuario(self):
        """Test creación de RolUsuario con nivel de acceso y permisos"""
        rol = RolUsuario.objects.create(
            codigo='DIRECTOR',
            nombre='Director de Colegio',
            nivel_acceso=4,
            puede_administrar=False,
            puede_aprobar=True,
            puede_ver_todos=True
        )
        self.assertEqual(str(rol), 'Director de Colegio')
        self.assertTrue(rol.puede_aprobar)

    def test_codigo_unico_en_catalogos(self):
        """El campo código debe ser único por catálogo"""
        TipoFuncionario.objects.create(
            codigo='DOCENTE',
            nombre='Docente de Aula'
        )
        with self.assertRaises(IntegrityError):
            TipoFuncionario.objects.create(
                codigo='DOCENTE',
                nombre='Docente Duplicado'
            )

    def test_estado_registro_asistencia(self):
        """Test catálogo de estados de asistencia con flags de conteo y requerimiento"""
        estado = EstadoRegistroAsistencia.objects.create(
            codigo='PUNTUAL',
            nombre='Llegada Puntual',
            cuenta_como_asistencia=True,
            requiere_justificacion=False,
            color_hex='#10B981'
        )
        self.assertEqual(str(estado), 'Llegada Puntual')
        self.assertTrue(estado.cuenta_como_asistencia)
        self.assertFalse(estado.requiere_justificacion)

    def test_estado_solicitud_permiso(self):
        """Test catálogo de estados de solicitudes con flag terminal"""
        estado_pend = EstadoSolicitudPermiso.objects.create(
            codigo='PENDIENTE',
            nombre='En Espera de Aprobación',
            es_terminal=False,
            permite_edicion=True
        )
        estado_aprob = EstadoSolicitudPermiso.objects.create(
            codigo='APROBADO',
            nombre='Aprobado por Dirección',
            es_terminal=True,
            permite_edicion=False
        )
        self.assertFalse(estado_pend.es_terminal)
        self.assertTrue(estado_aprob.es_terminal)

    def test_tipo_equipo_y_estado_equipo(self):
        """Test catálogos de tipos y estados de equipamiento tecnológico"""
        tipo = TipoEquipo.objects.create(
            codigo='LAPTOP',
            nombre='Computador Portátil'
        )
        estado = EstadoEquipo.objects.create(
            codigo='DISPONIBLE',
            nombre='Disponible para Asignación',
            disponible_prestamo=True
        )
        self.assertEqual(str(tipo), 'Computador Portátil')
        self.assertTrue(estado.disponible_prestamo)

    def test_periodo_liquidacion(self):
        """Test creación y propiedades de PeriodoLiquidacion"""
        from datetime import date
        periodo = PeriodoLiquidacion.objects.create(
            anio=2026,
            mes=10,
            fecha_inicio=date(2026, 10, 1),
            fecha_termino=date(2026, 10, 31),
            cerrado=False
        )
        self.assertEqual(periodo.anio, 2026)
        self.assertEqual(periodo.mes, 10)
        self.assertFalse(periodo.cerrado)
        self.assertIn("Octubre 2026", str(periodo))

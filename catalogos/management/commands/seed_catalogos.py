"""
Script para poblar los catálogos del sistema.
Ejecutar con: python manage.py seed_catalogos
"""
from django.core.management.base import BaseCommand
from catalogos.models import (
    RolUsuario,
    TipoFuncionario,
    EstadoRegistroAsistencia,
    EstadoSolicitudPermiso,
    TipoEquipo,
    EstadoEquipo,
    JornadaLaboral,
    TipoDia,
)
from datetime import datetime
from calendar import monthrange


class Command(BaseCommand):
    help = 'Pobla los catálogos del sistema con datos iniciales'

    def handle(self, *args, **options):
        self.stdout.write('🔄 Poblando catálogos del sistema...')
        
        # Roles de Usuario
        roles_data = [
            {'codigo': 'ADMIN', 'nombre': 'Administrador', 'descripcion': 'Usuario con acceso completo al sistema',
             'nivel_acceso': 5, 'puede_administrar': True, 'puede_aprobar': True, 'puede_ver_todos': True, 'orden': 1},
            {'codigo': 'SECRETARIA', 'nombre': 'Secretaria', 'descripcion': 'Secretaria con permisos de gestión',
             'nivel_acceso': 4, 'puede_administrar': True, 'puede_aprobar': True, 'puede_ver_todos': True, 'orden': 2},
            {'codigo': 'DIRECTOR', 'nombre': 'Director', 'descripcion': 'Director del establecimiento',
             'nivel_acceso': 4, 'puede_administrar': False, 'puede_aprobar': True, 'puede_ver_todos': True, 'orden': 3},
            {'codigo': 'DIRECTIVO', 'nombre': 'Directivo', 'descripcion': 'Personal directivo',
             'nivel_acceso': 3, 'puede_administrar': False, 'puede_aprobar': False, 'puede_ver_todos': True, 'orden': 4},
            {'codigo': 'FUNCIONARIO', 'nombre': 'Funcionario', 'descripcion': 'Funcionario regular',
             'nivel_acceso': 1, 'puede_administrar': False, 'puede_aprobar': False, 'puede_ver_todos': False, 'orden': 5},
        ]
        
        for data in roles_data:
            RolUsuario.objects.update_or_create(
                codigo=data['codigo'],
                defaults=data
            )
        self.stdout.write(self.style.SUCCESS(f'✅ {len(roles_data)} roles de usuario creados'))

        # Tipos de Funcionario
        tipos_funcionario = [
            {'codigo': 'DOCENTE', 'nombre': 'Docente', 'descripcion': 'Personal docente', 'orden': 1},
            {'codigo': 'ASISTENTE', 'nombre': 'Asistente de la Educación', 'descripcion': 'Personal asistente de la educación', 'orden': 2},
        ]
        
        for data in tipos_funcionario:
            TipoFuncionario.objects.update_or_create(
                codigo=data['codigo'],
                defaults=data
            )
        self.stdout.write(self.style.SUCCESS(f'✅ {len(tipos_funcionario)} tipos de funcionario creados'))

        # Estados de Asistencia
        estados_asistencia = [
            {'codigo': 'PUNTUAL', 'nombre': 'Puntual', 'descripcion': 'Llegó a tiempo',
             'cuenta_como_asistencia': True, 'requiere_justificacion': False, 'color_hex': '#10B981', 'orden': 1},
            {'codigo': 'RETRASO', 'nombre': 'Retraso', 'descripcion': 'Llegó con retraso',
             'cuenta_como_asistencia': True, 'requiere_justificacion': True, 'color_hex': '#F59E0B', 'orden': 2},
            {'codigo': 'AUSENTE', 'nombre': 'Ausente', 'descripcion': 'No asistió',
             'cuenta_como_asistencia': False, 'requiere_justificacion': True, 'color_hex': '#EF4444', 'orden': 3},
            {'codigo': 'JUSTIFICADO', 'nombre': 'Justificado', 'descripcion': 'Ausencia justificada',
             'cuenta_como_asistencia': True, 'requiere_justificacion': False, 'color_hex': '#3B82F6', 'orden': 4},
            {'codigo': 'DIA_ADMINISTRATIVO', 'nombre': 'Día Administrativo', 'descripcion': 'Día administrativo aprobado',
             'cuenta_como_asistencia': True, 'requiere_justificacion': False, 'color_hex': '#8B5CF6', 'orden': 5},
            {'codigo': 'LICENCIA_MEDICA', 'nombre': 'Licencia Médica', 'descripcion': 'Licencia médica vigente',
             'cuenta_como_asistencia': True, 'requiere_justificacion': False, 'color_hex': '#EC4899', 'orden': 6},
            {'codigo': 'DIA_FESTIVO', 'nombre': 'Día Festivo', 'descripcion': 'Día festivo o holiday',
             'cuenta_como_asistencia': True, 'requiere_justificacion': False, 'color_hex': '#14B8A6', 'orden': 7},
            {'codigo': 'SIN_HORARIO', 'nombre': 'Sin Horario', 'descripcion': 'No tiene horario asignado',
             'cuenta_como_asistencia': False, 'requiere_justificacion': False, 'color_hex': '#6B7280', 'orden': 8},
        ]
        
        for data in estados_asistencia:
            EstadoRegistroAsistencia.objects.update_or_create(
                codigo=data['codigo'],
                defaults=data
            )
        self.stdout.write(self.style.SUCCESS(f'✅ {len(estados_asistencia)} estados de asistencia creados'))

        # Estados de Solicitud de Permiso
        estados_permiso = [
            {'codigo': 'PENDIENTE', 'nombre': 'Pendiente', 'descripcion': 'Esperando aprobación',
             'es_terminal': False, 'permite_edicion': True, 'color_hex': '#F59E0B', 'orden': 1},
            {'codigo': 'APROBADO', 'nombre': 'Aprobado', 'descripcion': 'Solicitud aprobada',
             'es_terminal': True, 'permite_edicion': False, 'color_hex': '#10B981', 'orden': 2},
            {'codigo': 'RECHAZADO', 'nombre': 'Rechazado', 'descripcion': 'Solicitud rechazada',
             'es_terminal': True, 'permite_edicion': False, 'color_hex': '#EF4444', 'orden': 3},
            {'codigo': 'CANCELADO', 'nombre': 'Cancelado', 'descripcion': 'Solicitud cancelada',
             'es_terminal': True, 'permite_edicion': False, 'color_hex': '#6B7280', 'orden': 4},
        ]
        
        for data in estados_permiso:
            EstadoSolicitudPermiso.objects.update_or_create(
                codigo=data['codigo'],
                defaults=data
            )
        self.stdout.write(self.style.SUCCESS(f'✅ {len(estados_permiso)} estados de permiso creados'))

        # Tipos de Equipo
        tipos_equipo = [
            {'codigo': 'LAPTOP', 'nombre': 'Laptop', 'descripcion': 'Computador portátil', 'orden': 1},
            {'codigo': 'DESKTOP', 'nombre': 'Computador de Escritorio', 'descripcion': 'PC de escritorio', 'orden': 2},
            {'codigo': 'TABLET', 'nombre': 'Tablet', 'descripcion': 'Tableta digital', 'orden': 3},
            {'codigo': 'IMPRESORA', 'nombre': 'Impresora', 'descripcion': 'Impresora', 'orden': 4},
            {'codigo': 'MONITOR', 'nombre': 'Monitor', 'descripcion': 'Monitor externo', 'orden': 5},
            {'codigo': 'PROYECTOR', 'nombre': 'Proyector', 'descripcion': 'Proyector', 'orden': 6},
            {'codigo': 'CELULAR', 'nombre': 'Celular', 'descripcion': 'Teléfono móvil', 'orden': 7},
            {'codigo': 'OTRO', 'nombre': 'Otro', 'descripcion': 'Otro tipo de equipo', 'orden': 8},
        ]
        
        for data in tipos_equipo:
            TipoEquipo.objects.update_or_create(
                codigo=data['codigo'],
                defaults=data
            )
        self.stdout.write(self.style.SUCCESS(f'✅ {len(tipos_equipo)} tipos de equipo creados'))

        # Estados de Equipo
        estados_equipo = [
            {'codigo': 'DISPONIBLE', 'nombre': 'Disponible', 'descripcion': 'Equipo disponible para préstamo',
             'disponible_prestamo': True, 'color_hex': '#10B981', 'orden': 1},
            {'codigo': 'ASIGNADO', 'nombre': 'Asignado', 'descripcion': 'Equipo asignado a un funcionario',
             'disponible_prestamo': False, 'color_hex': '#3B82F6', 'orden': 2},
            {'codigo': 'EN_REPARACION', 'nombre': 'En Reparación', 'descripcion': 'Equipo en维修',
             'disponible_prestamo': False, 'color_hex': '#F59E0B', 'orden': 3},
            {'codigo': 'BAJA', 'nombre': 'De Baja', 'descripcion': 'Equipo dado de baja',
             'disponible_prestamo': False, 'color_hex': '#EF4444', 'orden': 4},
        ]
        
        for data in estados_equipo:
            EstadoEquipo.objects.update_or_create(
                codigo=data['codigo'],
                defaults=data
            )
        self.stdout.write(self.style.SUCCESS(f'✅ {len(estados_equipo)} estados de equipo creados'))

        # Jornadas Laborales
        jornadas = [
            {'codigo': 'AM', 'nombre': 'Mañana', 'descripcion': 'Jornada de mañana', 'horas': 4.0, 'orden': 1},
            {'codigo': 'PM', 'nombre': 'Tarde', 'descripcion': 'Jornada de tarde', 'horas': 4.0, 'orden': 2},
            {'codigo': 'FD', 'nombre': 'Día Completo', 'descripcion': 'Jornada completa', 'horas': 8.0, 'orden': 3},
        ]
        
        for data in jornadas:
            JornadaLaboral.objects.update_or_create(
                codigo=data['codigo'],
                defaults=data
            )
        self.stdout.write(self.style.SUCCESS(f'✅ {len(jornadas)} jornadas laborales creadas'))

        # Tipos de Día
        tipos_dia = [
            {'codigo': 'DIA_FESTIVO', 'nombre': 'Día Festivo', 'descripcion': 'Día festivo nacional o regional',
             'cuenta_como_asistencia': True, 'descuenta_dias': False, 'color_hex': '#14B8A6', 'orden': 1},
            {'codigo': 'DIA_ADMINISTRATIVO', 'nombre': 'Día Administrativo', 'descripcion': 'Día administrativo',
             'cuenta_como_asistencia': True, 'descuenta_dias': True, 'color_hex': '#8B5CF6', 'orden': 2},
            {'codigo': 'DIA_LICENCIA', 'nombre': 'Licencia Médica', 'descripcion': 'Día de licencia médica',
             'cuenta_como_asistencia': True, 'descuenta_dias': False, 'color_hex': '#EC4899', 'orden': 3},
            {'codigo': 'DIA_PERMISO', 'nombre': 'Día de Permiso', 'descripcion': 'Día de permiso',
             'cuenta_como_asistencia': True, 'descuenta_dias': True, 'color_hex': '#F59E0B', 'orden': 4},
        ]
        
        for data in tipos_dia:
            TipoDia.objects.update_or_create(
                codigo=data['codigo'],
                defaults=data
            )
        self.stdout.write(self.style.SUCCESS(f'✅ {len(tipos_dia)} tipos de día creados'))

        # Crear períodos de liquidaciones para el año actual y anterior
        current_year = datetime.now().year
        for year in [current_year - 1, current_year, current_year + 1]:
            for mes in range(1, 13):
                fecha_inicio = datetime(year, mes, 1).date()
                ultimo_dia = monthrange(year, mes)[1]
                fecha_termino = datetime(year, mes, ultimo_dia).date()
                
                # Solo crear períodos hasta el mes actual
                if year == current_year and mes > datetime.now().month:
                    activo = False
                elif year < current_year:
                    activo = False
                    cerrado = True
                else:
                    activo = True
                    cerrado = False
                    
                # El período se considera activo solo hasta el mes actual
                if year == current_year and mes <= datetime.now().month:
                    activo = True
                else:
                    activo = False
                    
                from catalogos.models import PeriodoLiquidacion
                PeriodoLiquidacion.objects.update_or_create(
                    mes=mes,
                    anio=year,
                    defaults={
                        'fecha_inicio': fecha_inicio,
                        'fecha_termino': fecha_termino,
                        'activo': activo,
                        'cerrado': cerrado if year < current_year else False
                    }
                )
        
        self.stdout.write(self.style.SUCCESS(f'✅ Períodos de liquidaciones creados'))

        self.stdout.write(self.style.SUCCESS('🎉 Catálogos poblados exitosamente!'))

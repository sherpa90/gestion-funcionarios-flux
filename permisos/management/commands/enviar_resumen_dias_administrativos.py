import logging
import os
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.mail import send_mail, send_mass_mail
from django.conf import settings
from django.db.models import Q
from django.db import connection
from django.utils import timezone
from users.models import CustomUser
from permisos.models import SolicitudPermiso
from licencias.models import LicenciaMedica
from asistencia.models import AnoEscolar
from core.models import SystemSettings
from django.template.loader import render_to_string

# Configurar logging a archivo
LOG_DIR = getattr(settings, 'LOG_DIR', os.path.join(settings.BASE_DIR, 'logs'))
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'resumen_diario_directores.log')

logger = logging.getLogger('resumen_diario')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


def get_pg_date():
    """Obtiene la fecha actual desde PostgreSQL en zona horaria America/Santiago."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT (now() AT TIME ZONE 'America/Santiago')::date")
        row = cursor.fetchone()
        return row[0] if row else date.today()


class Command(BaseCommand):
    help = 'Envía resumen diario de días administrativos y licencias a directores (lunes-viernes, periodo escolar)'

    def handle(self, *args, **options):
        hoy = get_pg_date()

        if hoy.weekday() >= 5:
            msg = 'Fin de semana: no se envía resumen'
            logger.info(msg)
            self.stdout.write(msg)
            return

        ano_escolar = AnoEscolar.objects.filter(activo=True).first()
        if not ano_escolar:
            msg = 'No hay año escolar activo'
            logger.info(msg)
            self.stdout.write(msg)
            return

        en_sem1 = ano_escolar.sem1_inicio <= hoy <= ano_escolar.sem1_fin
        en_sem2 = ano_escolar.sem2_inicio <= hoy <= ano_escolar.sem2_fin
        if not (en_sem1 or en_sem2):
            msg = 'Fuera de período lectivo: no se envía resumen'
            logger.info(msg)
            self.stdout.write(msg)
            return

        sys_settings = SystemSettings.get_solo()
        if not sys_settings.notifications_enabled or not sys_settings.director_daily_summary_enabled:
            msg = 'Resumen diario desactivado'
            logger.info(msg)
            self.stdout.write(msg)
            return

        directores = CustomUser.objects.filter(
            role='DIRECTOR', is_active=True,
            email__isnull=False, notifications_disabled=False
        ).exclude(email='')
        correos = [d.email for d in directores if d.categoria_funcionario == 'ADMINISTRATIVO']
        if not correos:
            msg = 'No hay directores con email'
            logger.info(msg)
            self.stdout.write(msg)
            return

        funcionarios = CustomUser.objects.filter(
            is_active=True
        ).select_related().order_by('funcion', 'last_name', 'first_name')
        funcionarios = [f for f in funcionarios if f.categoria_funcionario in ('DOCENTE', 'ASISTENTE')]

        permisos_hoy = SolicitudPermiso.objects.filter(
            estado='APROBADO',
            fecha_inicio__lte=hoy,
        ).filter(
            Q(fecha_termino__gte=hoy) | Q(fecha_termino__isnull=True)
        ).select_related('usuario')

        permisos_por_usuario = {}
        for p in permisos_hoy:
            permisos_por_usuario.setdefault(p.usuario_id, []).append(p)

        permisos_pendientes_hoy = SolicitudPermiso.objects.filter(
            estado='PENDIENTE',
            fecha_inicio__lte=hoy,
        ).filter(
            Q(fecha_termino__gte=hoy) | Q(fecha_termino__isnull=True)
        ).select_related('usuario')

        permisos_pendientes_por_usuario = {}
        for p in permisos_pendientes_hoy:
            permisos_pendientes_por_usuario.setdefault(p.usuario_id, []).append(p)

        licencias_hoy = LicenciaMedica.objects.filter(
            fecha_inicio__lte=hoy,
        )
        licencias_activas = {}
        for lic in licencias_hoy:
            fin_lic = lic.fecha_inicio + timedelta(days=lic.dias - 1)
            if fin_lic >= hoy:
                licencias_activas.setdefault(lic.usuario_id, []).append(lic)

        grupos = {}
        for f in funcionarios:
            cargo = f.get_funcion_display() or f.funcion or 'Sin cargo'
            grupos.setdefault(cargo, []).append(f)

        def build_section(titulo, cargos_ordenados):
            bloques = []
            for cargo in cargos_ordenados:
                items = []
                for f in grupos.get(cargo, []):
                    lineas = []
                    if f.id in permisos_pendientes_por_usuario:
                        for p in permisos_pendientes_por_usuario[f.id]:
                            if p.dias_solicitados == 0.5:
                                jornada = p.get_jornada_display()
                                lineas.append(f'<span style="color:#d97706;font-weight:600;">Pendiente ½ día {jornada}</span>')
                            else:
                                lineas.append('<span style="color:#d97706;font-weight:600;">Pendiente día administrativo</span>')
                    if f.id in permisos_por_usuario:
                        for p in permisos_por_usuario[f.id]:
                            if p.dias_solicitados == 0.5:
                                jornada = p.get_jornada_display()
                                lineas.append(f'<span style="color:#2563eb;">Medio día {jornada}</span>')
                            else:
                                lineas.append('<span style="color:#16a34a;">Día administrativo</span>')
                    if f.id in licencias_activas:
                        for lic in licencias_activas[f.id]:
                            tipo = lic.get_tipo_display()
                            fin = lic.fecha_inicio + timedelta(days=lic.dias - 1)
                            lineas.append(f'<span style="color:#dc2626;">Licencia {tipo} (hasta {fin.strftime("%d/%m")})</span>')
                    if lineas:
                        nombre = f.get_full_name() or f.username
                        items.append(f'<li style="margin-bottom:0.5rem;"><strong style="color:#111827;">{nombre}</strong>: {" • ".join(lineas)}</li>')
                if items:
                    bloques.append(f'<h4 style="margin:0.75rem 0 0.25rem;color:#4b5563;font-size:0.875rem;font-weight:600;">{cargo}</h4><ul style="margin:0;padding-left:1.25rem;">{"".join(items)}</ul>')
            if not bloques:
                return ''
            return bloques

        cargos_ordenados = sorted(grupos.keys())
        bloques_docentes = build_section('📚 Docentes', [c for c in cargos_ordenados if 'DOCENTE' in c or 'EDUCADORA' in c])
        bloques_asistentes = build_section('🏫 Asistentes y Otros', [c for c in cargos_ordenados if c not in cargos_ordenados or c not in [x for x in cargos_ordenados if 'DOCENTE' in x or 'EDUCADORA' in x]])

        hay_novedades = bool(bloques_docentes or bloques_asistentes)

        fecha_display = hoy.strftime("%A %d de %B de %Y").capitalize()
        hora_envio = sys_settings.director_daily_summary_time or '07:45'

        html = render_to_string('emails/resumen_diario_directores.html', {
            'fecha_display': fecha_display,
            'hora_envio': hora_envio,
            'html_docentes': '\n'.join(bloques_docentes) if bloques_docentes else '',
            'html_asistentes': '\n'.join(bloques_asistentes) if bloques_asistentes else '',
            'hay_novedades': hay_novedades,
        })

        subject = f'Resumen diario de ausencias administrativas — {hoy.strftime("%d/%m/%Y")}'
        from_email = settings.DEFAULT_FROM_EMAIL
        text_msg = f'Resumen diario del {hoy.strftime("%d/%m/%Y")}.\n\nVer versión HTML en cliente de correo.'

        enviados = 0
        errores = 0
        for email in correos:
            try:
                send_mail(
                    subject,
                    text_msg,
                    from_email,
                    [email],
                    fail_silently=False,
                    html_message=html,
                )
                enviados += 1
            except Exception as e:
                errores += 1
                logger.error(f'Error enviando a {email}: {e}', exc_info=True)

        msg = f'Resumen enviado a {enviados} director(es)'
        if errores:
            msg += f', {errores} error(es)'
        logger.info(msg)
        self.stdout.write(self.style.SUCCESS(msg) if enviados else self.style.ERROR('No se envió ningún correo'))

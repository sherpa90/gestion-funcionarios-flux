import threading
import logging
from django.core.mail import send_mail, send_mass_mail
from django.conf import settings
from users.models import CustomUser
from core.models import SystemSettings

logger = logging.getLogger(__name__)

class AsyncEmailThread(threading.Thread):
    def __init__(self, subject, message, from_email, recipient_list, html_message=None):
        self.subject = subject
        self.message = message
        self.from_email = from_email
        self.recipient_list = recipient_list
        self.html_message = html_message
        super().__init__()

    def run(self):
        try:
            send_mail(
                self.subject,
                self.message,
                self.from_email,
                self.recipient_list,
                fail_silently=False,
                html_message=self.html_message
            )
            logger.info(f"Correo enviado exitosamente a {self.recipient_list}")
        except Exception as e:
            logger.error(f"Error enviando correo a {self.recipient_list}: {e}")

class AsyncMassEmailThread(threading.Thread):
    def __init__(self, datatuple):
        self.datatuple = datatuple
        super().__init__()

    def run(self):
        try:
            send_mass_mail(self.datatuple, fail_silently=False)
            logger.info(f"Correos masivos enviados exitosamente a {len(self.datatuple)} destinatarios")
        except Exception as e:
            logger.error(f"Error enviando correos masivos: {e}")

def notify_director_new_request(solicitud):
    """Notifica a todos los directores de una nueva solicitud de día administrativo."""
    settings_obj = SystemSettings.get_solo()
    if not settings_obj.notifications_enabled:
        return
    directores = CustomUser.objects.filter(role='DIRECTOR', is_active=True, email__isnull=False, notifications_disabled=False)
    correos_directores = [d.email for d in directores if d.email]
    
    if not correos_directores:
        return

    subject = f"Nueva Solicitud de Permiso - {solicitud.usuario.get_full_name()}"
    message = (
        f"Se ha ingresado una nueva solicitud de día administrativo.\n\n"
        f"Funcionario: {solicitud.usuario.get_full_name()}\n"
        f"Fecha inicio: {solicitud.fecha_inicio}\n"
        f"Días solicitados: {solicitud.dias_solicitados}\n\n"
        f"Por favor revise el sistema para aprobar o rechazar esta solicitud."
    )
    
    datatuple = (
        (subject, message, settings.DEFAULT_FROM_EMAIL, [email])
        for email in correos_directores
    )
    AsyncMassEmailThread(tuple(datatuple)).start()

def notify_user_request_status(solicitud):
    """Notifica al funcionario sobre la respuesta de su solicitud."""
    settings_obj = SystemSettings.get_solo()
    if not settings_obj.notifications_enabled:
        return
    usuario = solicitud.usuario
    if usuario.notifications_disabled:
        return
    email = usuario.email
    if not email:
        return

    estado = solicitud.get_estado_display().lower()
    subject = f"Resolución de su Solicitud de Permiso"
    message = (
        f"Hola {usuario.first_name},\n\n"
        f"Su solicitud de permiso para la fecha {solicitud.fecha_inicio} ha sido {estado}.\n\n"
    )
    if solicitud.estado == 'RECHAZADO' and solicitud.motivo_rechazo:
        message += f"Motivo de rechazo: {solicitud.motivo_rechazo}\n\n"
    
    message += "Atte,\nDirección."
    
    AsyncEmailThread(subject, message, settings.DEFAULT_FROM_EMAIL, [email]).start()

def notify_all_users_liquidaciones(mes, anio):
    """Notifica a todos los funcionarios activos que se cargaron las liquidaciones."""
    settings_obj = SystemSettings.get_solo()
    if not settings_obj.liquidations_notifications_enabled:
        return
    funcionarios = CustomUser.objects.filter(is_active=True, email__isnull=False, notifications_disabled=False)
    correos = [f.email for f in funcionarios if f.email]
    
    if not correos:
        return

    from liquidaciones.models import get_mes_nombre
    mes_nombre = get_mes_nombre(mes)

    subject = f"Aviso de carga de Liquidaciones de Sueldo ({mes_nombre} {anio})"
    message = (
        f"Estimado(a) funcionario(a),\n\n"
        f"Le informamos que las liquidaciones de sueldo correspondientes al período {mes_nombre} {anio} ya están disponibles en el sistema.\n"
        f"Puede ingresar a su cuenta para revisarlas y descargarlas.\n\n"
        f"Atte,\nAdministración."
    )
    
    datatuple = (
        (subject, message, settings.DEFAULT_FROM_EMAIL, [email])
        for email in correos
    )
    AsyncMassEmailThread(tuple(datatuple)).start()

def notify_all_users_asistencia():
    """Notifica a todos los funcionarios activos que se cargó la asistencia."""
    settings_obj = SystemSettings.get_solo()
    if not settings_obj.attendance_notifications_enabled:
        return
    funcionarios = CustomUser.objects.filter(is_active=True, email__isnull=False, notifications_disabled=False)
    correos = [f.email for f in funcionarios if f.email]
    
    if not correos:
        return

    subject = "Aviso de carga de registros de Asistencia"
    message = (
        f"Estimado(a) funcionario(a),\n\n"
        f"Le informamos que se han cargado nuevos registros de asistencia al sistema.\n"
        f"Le invitamos a revisar sus marcaciones desde el portal.\n\n"
        f"Atte,\nAdministración."
    )
    
    datatuple = (
        (subject, message, settings.DEFAULT_FROM_EMAIL, [email])
        for email in correos
    )
    AsyncMassEmailThread(tuple(datatuple)).start()

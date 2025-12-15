from .models import SystemLog

def registrar_log(usuario, tipo, accion, descripcion, ip_address=None, metadata=None):
    return SystemLog.objects.create(
        usuario=usuario,
        tipo=tipo,
        accion=accion,
        descripcion=descripcion,
        ip_address=ip_address or '127.0.0.1',
        metadata=metadata or {}
    )

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

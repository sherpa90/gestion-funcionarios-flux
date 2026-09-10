from django.utils import timezone

def server_clock(request):
    now = timezone.localtime()
    return {
        'server_now': now.date(),
        'server_time': now.strftime('%H:%M:%S'),
        'server_timestamp': int(now.timestamp() * 1000),
    }

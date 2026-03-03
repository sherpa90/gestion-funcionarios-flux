from django.conf import settings

class CSPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Only apply CSP if we have it in settings and we're not in debug mode
        if hasattr(settings, 'SECURE_CONTENT_SECURITY_POLICY') and not getattr(settings, 'DEBUG', False):
            response['Content-Security-Policy'] = settings.SECURE_CONTENT_SECURITY_POLICY
            
        return response

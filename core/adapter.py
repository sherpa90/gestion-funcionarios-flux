from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Bloquea el registro de nuevos usuarios vía formulario.
    El alta de usuarios es exclusiva del administrador desde el panel de FLUX.
    """

    def is_open_for_signup(self, request):
        return False


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adaptador personalizado para restringir el inicio de sesión de Google
    únicamente a usuarios previamente registrados en la plataforma FLUX.
    """

    def is_open_for_signup(self, request, sociallogin):
        """
        Bloquea completamente el registro de nuevos usuarios vía Google.
        Solo usuarios ya existentes en el sistema pueden iniciar sesión.
        El alta de nuevos usuarios es exclusiva del administrador.
        """
        return False

    def pre_social_login(self, request, sociallogin):
        # Si el usuario ya está autenticado en la sesión actual
        if request.user.is_authenticated:
            return

        # Extraer el correo electrónico desde la cuenta social de Google
        email = None
        if sociallogin.account and sociallogin.account.extra_data:
            email = sociallogin.account.extra_data.get('email')
        if not email and sociallogin.user:
            email = sociallogin.user.email

        if not email:
            messages.error(
                request,
                "No se obtuvo un correo electrónico válido desde Google. "
                "Por favor intente nuevamente."
            )
            raise ImmediateHttpResponse(redirect('login'))

        # Buscar usuario en la base de datos de FLUX por email (case-insensitive)
        try:
            user = User.objects.get(email__iexact=email)

            # Verificar si la cuenta de usuario está bloqueada
            if getattr(user, 'is_blocked', False):
                messages.error(
                    request,
                    "Su cuenta de usuario se encuentra bloqueada. "
                    "Contacte al administrador del sistema."
                )
                raise ImmediateHttpResponse(redirect('login'))

            # Si el usuario existe pero no está enlazado a sociallogin todavía
            if not sociallogin.is_existing:
                sociallogin.connect(request, user)

        except User.DoesNotExist:
            request.session['social_login_email'] = email
            messages.error(
                request,
                f"La cuenta de Google ({email}) no está registrada en el sistema FLUX. "
                "Contacte al administrador institucional para obtener acceso."
            )
            raise ImmediateHttpResponse(redirect('login'))

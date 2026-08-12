from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class EmailBackend(ModelBackend):
    """
    Backend de autenticación que permite iniciar sesión con Email.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)

        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            return None
        else:
            if user.is_blocked:
                return None
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None


class RestrictedSocialLoginBackend:
    """
    Backend para restringir login social a usuarios existentes.
    Este backend se utiliza para validar que el email de Google
    corresponde a un usuario existente en el sistema.
    """
    def authenticate(self, request, email=None, **kwargs):
        if not email:
            return None
        try:
            user = User.objects.get(email__iexact=email)
            if user.is_blocked:
                return None
            return user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

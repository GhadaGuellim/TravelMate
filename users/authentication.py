from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from .models import User


class AuthenticatedUser:
    """Enveloppe le document MongoDB pour que DRF le reconnaisse comme connecté."""

    is_authenticated = True
    is_anonymous = False

    def __init__(self, user):
        self.user = user
        self.id = str(user.id)
        self.email = user.email
        self.full_name = user.full_name


class MongoJWTAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        parts = get_authorization_header(request).split()

        if not parts or parts[0].decode().lower() != self.keyword.lower():
            return None
        if len(parts) != 2:
            raise AuthenticationFailed("En-tête Authorization invalide.")

        try:
            token = AccessToken(parts[1].decode())
        except TokenError:
            raise AuthenticationFailed("Token invalide ou expiré.")

        try:
            user = User.objects(id=token["user_id"]).first()
        except Exception:
            user = None
        if not user:
            raise AuthenticationFailed("Utilisateur introuvable.")

        return (AuthenticatedUser(user), token)

    def authenticate_header(self, request):
        return self.keyword


class MongoJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "users.authentication.MongoJWTAuthentication"
    name = "BearerAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
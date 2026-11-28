from django.http import JsonResponse
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken

from users.models import User

EXEMPT = ("/api/auth/login/", "/api/auth/register/")


class BlockedUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer ") and request.path.startswith("/api/") and request.path not in EXEMPT:
            try:
                token = AccessToken(header.split(" ", 1)[1])
                user = User.objects(id=token[api_settings.USER_ID_CLAIM]).first()
            except Exception:
                user = None
            message = user.block_message() if user else ""
            if message:
                return JsonResponse({"error": message, "code": "account_suspended"}, status=403)
        return self.get_response(request)
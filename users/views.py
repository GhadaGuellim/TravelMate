from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import (
    LoginSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
)


def get_tokens(user):
    refresh = RefreshToken()
    refresh["user_id"] = str(user.id)
    refresh["email"] = user.email
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


def user_data(user):
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "bio": user.bio or "",
        "city": user.city or "",
        "country": user.country or "",
        "preferences": user.preferences or "",
        "avatar_url": user.avatar_url or "",
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }

class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterSerializer,
        responses={201: OpenApiTypes.OBJECT},
        tags=["Auth"],
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        email = data["email"].lower()

        if User.objects(email=email).first():
            return Response(
                {"error": "Cet email est déjà utilisé."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User(email=email, full_name=data["full_name"])
        user.set_password(data["password"])
        user.save()

        return Response(
            {"user": user_data(user), "tokens": get_tokens(user)},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={200: OpenApiTypes.OBJECT},
        tags=["Auth"],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = User.objects(email=data["email"].lower()).first()
        if not user or not user.verify_password(data["password"]):
            return Response(
                {"error": "Email ou mot de passe incorrect."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response({"user": user_data(user), "tokens": get_tokens(user)})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["Auth"])
    def get(self, request):
        return Response(user_data(request.user.user))

    @extend_schema(
        request=ProfileUpdateSerializer,
        responses={200: OpenApiTypes.OBJECT},
        tags=["Auth"],
    )
    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user.user
        for field, value in serializer.validated_data.items():
            setattr(user, field, value)
        user.save()

        return Response(user_data(user))
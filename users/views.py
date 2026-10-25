from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import ValidationError
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
        "role": user.role,
        "bio": user.bio or "",
        "city": user.city or "",
        "country": user.country or "",
        "preferences": user.preferences or "",
        "avatar_url": user.avatar_url or "",
        "service_type": user.service_type,
        "service_description": user.service_description,
        "service_location": user.service_location,
        "phone": user.phone,
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

        user = User(email=email, full_name=data["full_name"], role=data["role"])
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

PROVIDER_FIELDS = {"service_type", "service_description", "service_location", "phone"}

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
        data = serializer.validated_data

        user = request.user.user

        if user.role != "provider":
            data = {k: v for k, v in data.items() if k not in PROVIDER_FIELDS}
        else:
            errors = {}
            if "service_type" in data and not data["service_type"]:
                errors["service_type"] = "Le type de service est obligatoire."
            if "phone" in data and not data["phone"].strip():
                errors["phone"] = "Le téléphone est obligatoire."
            if errors:
                raise ValidationError(errors)

        for field, value in data.items():
            setattr(user, field, value)
        user.save()

        return Response(user_data(user))


class UserProfileView(APIView):
    """US12 – GET : consulter le profil public d'un voyageur avec compteurs."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["Utilisateurs"])
    def get(self, request, user_id):
        me = request.user.user
        target = User.objects(id=user_id).first()
        if not target:
            raise NotFound("Utilisateur introuvable.")

        followers_count = User.objects(following=target).count()
        following_count = len(target.following or [])
        is_following = target in (me.following or [])

        return Response(
            {
                **user_data(target),
                "followers_count": followers_count,
                "following_count": following_count,
                "is_following": is_following,
            }
        )


class FollowView(APIView):
    """US12 – POST : basculer suivre / ne plus suivre un voyageur."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT}, tags=["Utilisateurs"])
    def post(self, request, user_id):
        me = request.user.user
        target = User.objects(id=user_id).first()
        if not target:
            raise NotFound("Utilisateur introuvable.")
        if str(target.id) == str(me.id):
            return Response(
                {"error": "Vous ne pouvez pas vous suivre vous-même."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if target in (me.following or []):
            # Unfollow
            me.update(pull__following=target)
            following = False
        else:
            # Follow
            me.update(add_to_set__following=target)
            following = True

        me.reload()
        followers_count = User.objects(following=target).count()
        return Response(
            {
                "following": following,
                "followers_count": followers_count,
            }
        )


def user_card(u):
    return {
        "id": str(u.id),
        "full_name": u.full_name,
        "avatar_url": u.avatar_url or "",
        "city": u.city or "",
        "country": u.country or "",
    }


class FollowingListView(APIView):
    """Les voyageurs que je suis."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        me = request.user.user
        me.reload()
        # on ignore les comptes supprimés (références cassées)
        users = [u for u in me.following if hasattr(u, "full_name")]
        return Response([user_card(u) for u in users])


class SuggestionsView(APIView):
    """Voyageurs que je ne suis pas encore."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        me = request.user.user
        me.reload()
        excluded = [me.id] + [u.id for u in me.following]
        users = User.objects(id__nin=excluded).order_by("-created_at").limit(8)
        return Response([user_card(u) for u in users])
from datetime import datetime, timezone

from mongoengine.errors import DoesNotExist
from mongoengine.errors import ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken

from users.models import User

from .models import Review
from .serializers import ReviewSerializer


def get_current_user(request):
    """Lit le token JWT et retourne l'utilisateur MongoDB, ou None."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        token = AccessToken(header.split(" ", 1)[1])
        return User.objects.get(id=token[api_settings.USER_ID_CLAIM])
    except (TokenError, DoesNotExist, MongoValidationError, KeyError):
        return None


def unauthorized():
    return Response(
        {"detail": "Authentification requise."}, status=status.HTTP_401_UNAUTHORIZED
    )


class ReviewListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        filters = {}
        target_type = request.query_params.get("target_type")
        target_id = request.query_params.get("target_id")
        if target_type:
            filters["target_type"] = target_type
        if target_id:
            filters["target_id"] = target_id

        reviews = list(Review.objects(**filters).order_by("-created_at"))
        count = len(reviews)
        average = round(sum(r.rating for r in reviews) / count, 2) if count else 0

        return Response(
            {
                "count": count,
                "average": average,
                "results": ReviewSerializer(reviews, many=True).data,
            }
        )

    def post(self, request):
        user = get_current_user(request)
        if user is None:
            return unauthorized()

        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        already = Review.objects(
            author=user,
            target_type=data["target_type"],
            target_id=data["target_id"],
        ).first()
        if already:
            return Response(
                {"detail": "Vous avez déjà donné un avis pour cet élément."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        review = Review(
            author=user,
            target_type=data["target_type"],
            target_id=data["target_id"],
            rating=data["rating"],
            comment=data.get("comment", ""),
        ).save()

        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class ReviewDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get_review(self, pk):
        try:
            return Review.objects.get(id=pk)
        except (DoesNotExist, MongoValidationError):
            return None

    def put(self, request, pk):
        user = get_current_user(request)
        if user is None:
            return unauthorized()

        review = self.get_review(pk)
        if review is None:
            return Response(
                {"detail": "Avis introuvable."}, status=status.HTTP_404_NOT_FOUND
            )
        if review.author.id != user.id:
            return Response(
                {"detail": "Vous ne pouvez modifier que vos propres avis."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ReviewSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "rating" in data:
            review.rating = data["rating"]
        if "comment" in data:
            review.comment = data["comment"]
        review.updated_at = datetime.now(timezone.utc)
        review.save()

        return Response(ReviewSerializer(review).data)

    def delete(self, request, pk):
        user = get_current_user(request)
        if user is None:
            return unauthorized()

        review = self.get_review(pk)
        if review is None:
            return Response(
                {"detail": "Avis introuvable."}, status=status.HTTP_404_NOT_FOUND
            )
        if review.author.id != user.id:
            return Response(
                {"detail": "Vous ne pouvez supprimer que vos propres avis."},
                status=status.HTTP_403_FORBIDDEN,
            )

        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
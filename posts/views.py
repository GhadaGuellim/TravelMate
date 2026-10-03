from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Post
from .serializers import PostSerializer


def post_data(post):
    return {
        "id": str(post.id),
        "text": post.text,
        "destination": post.destination,
        "author": {
            "id": str(post.author.id),
            "full_name": post.author.full_name,
        },
        "created_at": post.created_at.isoformat() if post.created_at else None,
    }


class PostCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PostSerializer,
        responses={201: OpenApiTypes.OBJECT},
        tags=["Publications"],
    )
    def post(self, request):
        serializer = PostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = Post(author=request.user.user, **serializer.validated_data)
        post.save()
        return Response(post_data(post), status=status.HTTP_201_CREATED)


class FeedView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["Publications"])
    def get(self, request):
        posts = Post.objects.order_by("-created_at").limit(50)
        return Response([post_data(p) for p in posts])
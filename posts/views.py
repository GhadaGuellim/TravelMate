import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from mongoengine.errors import ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Comment, Post, now
from .serializers import CommentSerializer, PostSerializer, PostUpdateSerializer


def get_post(post_id):
    try:
        post = Post.objects(id=post_id).first()
    except MongoValidationError:
        post = None
    if not post:
        raise NotFound("Publication introuvable.")
    return post


def author_data(user):
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "avatar_url": user.avatar_url or "",
    }

def comment_data(c):
    return {
        "id": str(c.id),
        "text": c.text,
        "author": author_data(c.author),
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def post_data(post, me, request=None):
    image = post.image or ""
    if image and not image.startswith(("http://", "https://")):
        # chemin relatif : on construit une URL complète
        url = f"{settings.MEDIA_URL}{image}"
        image = request.build_absolute_uri(url) if request else url

    return {
        "id": str(post.id),
        "text": post.text,
        "destination": post.destination,
        "image": image,
        "author": author_data(post.author),
        "likes_count": len(post.likes),
        "liked_by_me": me in post.likes,
        "saved_by_me": me in post.saved_by,
        "comments_count": len(post.comments),
        "comments": [comment_data(c) for c in post.comments],
        "is_mine": post.author.id == me.id,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
    }


def save_image(request, file):
    name = f"posts/{uuid.uuid4().hex}_{file.name}"
    path = default_storage.save(name, file)
    return request.build_absolute_uri(settings.MEDIA_URL + path)


class PostListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["Publications"])
    def get(self, request):
        me = request.user.user
        qs = Post.objects
        author = request.query_params.get("author")
        destination = request.query_params.get("destination")
        if author:
            qs = qs.filter(author=author)
        if destination:
            qs = qs.filter(destination__iexact=destination)
        limit = min(int(request.query_params.get("limit", 20)), 50)
        skip = int(request.query_params.get("skip", 0))
        posts = qs.order_by("-created_at").skip(skip).limit(limit)
        return Response([post_data(p, me) for p in posts])

    @extend_schema(
        request=PostSerializer, responses={201: OpenApiTypes.OBJECT}, tags=["Publications"]
    )
    def post(self, request):
        me = request.user.user
        serializer = PostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        image = data.pop("image", None)
        post = Post(author=me, **data)
        if image:
            post.image = save_image(request, image)
        post.save()
        return Response(post_data(post, me), status=status.HTTP_201_CREATED)


class PostDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["Publications"])
    def get(self, request, post_id):
        return Response(post_data(get_post(post_id), request.user.user))

    @extend_schema(
        request=PostUpdateSerializer,
        responses={200: OpenApiTypes.OBJECT},
        tags=["Publications"],
    )
    def patch(self, request, post_id):
        me = request.user.user
        post = get_post(post_id)
        if post.author.id != me.id:
            raise PermissionDenied("Ce n'est pas ta publication.")
        serializer = PostUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for key, value in serializer.validated_data.items():
            setattr(post, key, value)
        post.updated_at = now()
        post.save()
        return Response(post_data(post, me))

    @extend_schema(responses={204: None}, tags=["Publications"])
    def delete(self, request, post_id):
        post = get_post(post_id)
        if post.author.id != request.user.user.id:
            raise PermissionDenied("Ce n'est pas ta publication.")
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PostLikeView(APIView):
    """POST = bascule like / unlike."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT}, tags=["Publications"])
    def post(self, request, post_id):
        me = request.user.user
        post = get_post(post_id)
        if me in post.likes:
            post.update(pull__likes=me)
        else:
            post.update(add_to_set__likes=me)
        post.reload()
        return Response({"liked": me in post.likes, "likes_count": len(post.likes)})


class PostSaveView(APIView):
    """POST = bascule enregistrer / retirer."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT}, tags=["Publications"])
    def post(self, request, post_id):
        me = request.user.user
        post = get_post(post_id)
        if me in post.saved_by:
            post.update(pull__saved_by=me)
        else:
            post.update(add_to_set__saved_by=me)
        post.reload()
        return Response({"saved": me in post.saved_by})


class SavedPostsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["Publications"])
    def get(self, request):
        me = request.user.user
        posts = Post.objects(saved_by=me).order_by("-created_at").limit(50)
        return Response([post_data(p, me) for p in posts])


class CommentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CommentSerializer, responses={201: OpenApiTypes.OBJECT}, tags=["Publications"]
    )
    def post(self, request, post_id):
        me = request.user.user
        post = get_post(post_id)
        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = Comment(author=me, text=serializer.validated_data["text"])
        post.update(push__comments=comment)
        return Response(comment_data(comment), status=status.HTTP_201_CREATED)


class CommentDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={204: None}, tags=["Publications"])
    def delete(self, request, post_id, comment_id):
        me = request.user.user
        post = get_post(post_id)
        comment = next((c for c in post.comments if str(c.id) == comment_id), None)
        if not comment:
            raise NotFound("Commentaire introuvable.")
        if comment.author.id != me.id and post.author.id != me.id:
            raise PermissionDenied("Tu ne peux pas supprimer ce commentaire.")
        post.update(pull__comments__id=comment.id)
        return Response(status=status.HTTP_204_NO_CONTENT)
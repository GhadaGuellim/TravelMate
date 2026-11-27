import re

from mongoengine.errors import DoesNotExist, NotUniqueError
from mongoengine.errors import ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CommunityComment, Community, CommunityPost

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

IMAGE_RE = re.compile(r"^data:image/(png|jpe?g|webp|gif);base64,")
MAX_IMAGE_CHARS = 1_500_000  # ~1,1 Mo d'image une fois décodée


def interests_of(user):
    """Centres d'intérêt du profil : "Culture, Nature" -> {"culture", "nature"}."""
    raw = user.preferences or ""
    return {p.strip().lower() for p in re.split(r"[,;/|]", raw) if p.strip()}


def member_ids_of(community):
    return {str(getattr(m, "id", m)) for m in community.members}


def is_member(community, user):
    return str(user.id) in member_ids_of(community)


def serialize(community, user, interests):
    topics = list(community.topics)
    common = [t for t in topics if t.lower() in interests]
    member_ids = member_ids_of(community)
    return {
        "id": str(community.id),
        "name": community.name,
        "description": community.description or "",
        "cover_image": community.cover_image or "",
        "topics": topics,
        "members_count": len(member_ids),
        "is_member": str(user.id) in member_ids,
        "match": len(common),
        "common_topics": common,
    }


def author_name(user):
    """Nom affiché d'un auteur : full_name, jamais l'email."""
    if user is None:
        return "Utilisateur supprimé"
    full = (getattr(user, "full_name", "") or "").strip()
    if not full:
        full = f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}".strip()
    return full or getattr(user, "username", None) or "Utilisateur"


def serialize_author(user):
    return {"id": str(user.id) if user else None, "name": author_name(user)}


def serialize_post(post, user):
    return {
        "id": str(post.id),
        "community": str(post.community.id),
        "author": serialize_author(post.author),
        "content": post.content,
        "image": post.image or "",
        "created_at": post.created_at.isoformat(),
        "comments_count": CommunityComment.objects(post=post).count(),
        "likes_count": len(post.likes),
        "liked": user.id in post.likes,
        "is_author": str(post.author.id) == str(user.id),
    }


def serialize_comment(comment, user):
    return {
        "id": str(comment.id),
        "post": str(comment.post.id),
        "author": serialize_author(comment.author),
        "content": comment.content,
        "created_at": comment.created_at.isoformat(),
        "is_author": str(comment.author.id) == str(user.id),
    }


def get_community(pk):
    try:
        return Community.objects.get(id=pk)
    except (DoesNotExist, MongoValidationError):
        return None


def get_post(community, post_id):
    try:
        return CommunityPost.objects.get(id=post_id, community=community)
    except (DoesNotExist, MongoValidationError):
        return None


def get_comment(post, comment_id):
    try:
        return CommunityComment.objects.get(id=comment_id, post=post)
    except (DoesNotExist, MongoValidationError):
        return None


def not_found(message="Communauté introuvable."):
    return Response({"detail": message}, status=status.HTTP_404_NOT_FOUND)


def forbidden(message):
    return Response({"detail": message}, status=status.HTTP_403_FORBIDDEN)


def bad_request(errors):
    return Response(errors, status=status.HTTP_400_BAD_REQUEST)


def clean_text(value, max_length):
    """Retourne (texte nettoyé, erreur)."""
    text = (value or "").strip() if isinstance(value, str) else ""
    if not text:
        return None, "Ce champ est obligatoire."
    if len(text) > max_length:
        return None, f"Maximum {max_length} caractères."
    return text, None


# --------------------------------------------------------------------------
# Communautés
# --------------------------------------------------------------------------


class CommunityListView(APIView):
    """GET : toutes les communautés (les plus proches de mes intérêts en premier).
    POST : créer une communauté (le créateur en devient le premier membre)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user.user
        interests = interests_of(user)
        items = [serialize(c, user, interests) for c in Community.objects]
        items.sort(key=lambda c: (-c["match"], -c["members_count"], c["name"]))
        return Response(items)

    def post(self, request):
        user = request.user.user
        data = request.data
        errors = {}

        name, err = clean_text(data.get("name"), 100)
        if err:
            errors["name"] = err
        elif Community.objects(name__iexact=name).first():
            errors["name"] = "Une communauté porte déjà ce nom."

        description = (data.get("description") or "").strip()
        if len(description) > 500:
            errors["description"] = "Maximum 500 caractères."

        cover_image = (data.get("cover_image") or "").strip()
        if len(cover_image) > 500:
            errors["cover_image"] = "Maximum 500 caractères."

        raw_topics = data.get("topics") or []
        if isinstance(raw_topics, str):
            raw_topics = re.split(r"[,;/|]", raw_topics)
        if not isinstance(raw_topics, list):
            errors["topics"] = "Une liste de thèmes est attendue."
            topics = []
        else:
            topics = []
            for t in raw_topics:
                t = str(t).strip()
                if t and t.lower() not in {x.lower() for x in topics}:
                    topics.append(t)
            if any(len(t) > 50 for t in topics):
                errors["topics"] = "Chaque thème : 50 caractères maximum."

        if errors:
            return bad_request(errors)

        try:
            community = Community(
                name=name,
                description=description,
                cover_image=cover_image,
                topics=topics,
                members=[user],
                created_by=user,
            ).save()
        except NotUniqueError:
            return bad_request({"name": "Une communauté porte déjà ce nom."})

        return Response(
            serialize(community, user, interests_of(user)),
            status=status.HTTP_201_CREATED,
        )


class MyCommunitiesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user.user
        interests = interests_of(user)
        items = [serialize(c, user, interests) for c in Community.objects(members=user)]
        items.sort(key=lambda c: c["name"])
        return Response(items)


class CommunityDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = request.user.user
        community = get_community(pk)
        if community is None:
            return not_found()
        return Response(serialize(community, user, interests_of(user)))


class JoinCommunityView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user.user
        community = get_community(pk)
        if community is None:
            return not_found()

        community.update(add_to_set__members=user)
        community.reload()
        return Response(serialize(community, user, interests_of(user)))


class LeaveCommunityView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user.user
        community = get_community(pk)
        if community is None:
            return not_found()

        community.update(pull__members=user)
        community.reload()
        return Response(serialize(community, user, interests_of(user)))


# --------------------------------------------------------------------------
# Publications
# --------------------------------------------------------------------------


class PostListCreateView(APIView):
    """GET : fil de la communauté (paginé, plus récent d'abord).
    POST : publier (réservé aux membres)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = request.user.user
        community = get_community(pk)
        if community is None:
            return not_found()

        try:
            page = max(int(request.query_params.get("page", 1)), 1)
            limit = min(max(int(request.query_params.get("limit", 20)), 1), 50)
        except ValueError:
            return bad_request({"detail": "Paramètres de pagination invalides."})

        qs = CommunityPost.objects(community=community)
        total = qs.count()
        posts = qs.skip((page - 1) * limit).limit(limit)
        return Response(
            {
                "count": total,
                "page": page,
                "limit": limit,
                "results": [serialize_post(p, user) for p in posts],
            }
        )

    def post(self, request, pk):
        user = request.user.user
        community = get_community(pk)
        if community is None:
            return not_found()
        if not is_member(community, user):
            return forbidden("Rejoins la communauté pour publier.")

        content, err = clean_text(request.data.get("content"), 2000)
        if err:
            return bad_request({"content": err})

        image = (request.data.get("image") or "").strip()
        if image:
            if not IMAGE_RE.match(image):
                return bad_request({"image": "Format d'image non valide."})
            if len(image) > MAX_IMAGE_CHARS:
                return bad_request({"image": "Image trop lourde."})

        post = CommunityPost(community=community, author=user, content=content, image=image).save()
        return Response(serialize_post(post, user), status=status.HTTP_201_CREATED)


class PostDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, post_id):
        user = request.user.user
        community = get_community(pk)
        if community is None:
            return not_found()
        post = get_post(community, post_id)
        if post is None:
            return not_found("Publication introuvable.")
        return Response(serialize_post(post, user))

    def delete(self, request, pk, post_id):
        """Supprimable par son auteur ou par le créateur de la communauté."""
        user = request.user.user
        community = get_community(pk)
        if community is None:
            return not_found()
        post = get_post(community, post_id)
        if post is None:
            return not_found("Publication introuvable.")

        is_author = str(post.author.id) == str(user.id)
        is_owner = community.created_by and str(community.created_by.id) == str(user.id)
        if not (is_author or is_owner):
            return forbidden("Tu ne peux pas supprimer cette publication.")

        CommunityComment.objects(post=post).delete()
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PostLikeView(APIView):
    """Aime / n'aime plus une publication (réservé aux membres)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk, post_id):
        user = request.user.user
        community = get_community(pk)
        if community is None:
            return not_found()
        post = get_post(community, post_id)
        if post is None:
            return not_found("Publication introuvable.")
        if not is_member(community, user):
            return forbidden("Rejoins la communauté pour aimer une publication.")

        if user.id in post.likes:
            post.update(pull__likes=user.id)
        else:
            post.update(add_to_set__likes=user.id)
        post.reload()
        return Response(serialize_post(post, user))


# --------------------------------------------------------------------------
# Commentaires
# --------------------------------------------------------------------------


class CommentListCreateView(APIView):
    """GET : commentaires d'une publication (ancien -> récent).
    POST : commenter (réservé aux membres)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk, post_id):
        user = request.user.user
        community = get_community(pk)
        if community is None:
            return not_found()
        post = get_post(community, post_id)
        if post is None:
            return not_found("Publication introuvable.")
        return Response([serialize_comment(c, user) for c in CommunityComment.objects(post=post)])

    def post(self, request, pk, post_id):
        user = request.user.user
        community = get_community(pk)
        if community is None:
            return not_found()
        post = get_post(community, post_id)
        if post is None:
            return not_found("Publication introuvable.")
        if not is_member(community, user):
            return forbidden("Rejoins la communauté pour commenter.")

        content, err = clean_text(request.data.get("content"), 1000)
        if err:
            return bad_request({"content": err})

        comment = CommunityComment(post=post, author=user, content=content).save()
        return Response(serialize_comment(comment, user), status=status.HTTP_201_CREATED)


class CommentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, post_id, comment_id):
        """Supprimable par son auteur ou par le créateur de la communauté."""
        user = request.user.user
        community = get_community(pk)
        if community is None:
            return not_found()
        post = get_post(community, post_id)
        if post is None:
            return not_found("Publication introuvable.")
        comment = get_comment(post, comment_id)
        if comment is None:
            return not_found("Commentaire introuvable.")

        is_author = str(comment.author.id) == str(user.id)
        is_owner = community.created_by and str(community.created_by.id) == str(user.id)
        if not (is_author or is_owner):
            return forbidden("Tu ne peux pas supprimer ce commentaire.")

        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
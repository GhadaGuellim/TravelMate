import re

from mongoengine.errors import DoesNotExist
from mongoengine.errors import ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Community


def interests_of(user):
    """Centres d'intérêt du profil : "Culture, Nature" -> {"culture", "nature"}."""
    raw = user.preferences or ""
    return {p.strip().lower() for p in re.split(r"[,;/|]", raw) if p.strip()}


def serialize(community, user, interests):
    topics = list(community.topics)
    common = [t for t in topics if t.lower() in interests]
    member_ids = {str(getattr(m, "id", m)) for m in community.members}
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


def get_community(pk):
    try:
        return Community.objects.get(id=pk)
    except (DoesNotExist, MongoValidationError):
        return None


def not_found():
    return Response(
        {"detail": "Communauté introuvable."}, status=status.HTTP_404_NOT_FOUND
    )


class CommunityListView(APIView):
    """Toutes les communautés, les plus proches de mes intérêts en premier."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user.user
        interests = interests_of(user)
        items = [serialize(c, user, interests) for c in Community.objects]
        items.sort(key=lambda c: (-c["match"], -c["members_count"], c["name"]))
        return Response(items)


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
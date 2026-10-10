from django.shortcuts import render

# Create your views here.
from django.conf import settings
from django.utils.dateparse import parse_datetime
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from mongoengine import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from posts.models import Post
from posts.views import post_data

from .models import Destination


# ---------- Helpers ----------

def cover_url(request, cover):
    if not cover:
        return ""
    if cover.startswith(("http://", "https://")):
        return cover
    url = f"{settings.MEDIA_URL}{cover}"
    return request.build_absolute_uri(url) if request else url


def destination_data(dest, posts_count, request=None):
    return {
        "id": str(dest.id),
        "slug": dest.slug,
        "name": dest.name,
        "country": dest.country,
        "description": dest.description,
        "cover_url": cover_url(request, dest.cover),
        "best_season": dest.best_season,
        "avg_budget": dest.avg_budget,
        "tags": list(dest.tags or []),
        "posts_count": posts_count,
    }


def posts_counts(destinations):
    """Nombre de publications par destination, en UNE requête d'agrégation.
    Une publication compte si son champ « destination » contient le nom."""
    rows = Post._get_collection().aggregate([
        {"$match": {"destination": {"$nin": ["", None]}}},
        {"$group": {"_id": "$destination", "n": {"$sum": 1}}},
    ])
    totals = [(row["_id"].lower(), row["n"]) for row in rows]
    return {
        d.slug: sum(n for text, n in totals if d.name.lower() in text)
        for d in destinations
    }


def _limit(request, default, maximum):
    try:
        return min(max(int(request.query_params.get("limit", default)), 1), maximum)
    except ValueError:
        return default


def _get_destination(slug):
    return Destination.objects(slug=slug.lower()).first()


def _not_found():
    return Response({"error": "Destination introuvable."}, status=status.HTTP_404_NOT_FOUND)


# ---------- Vues ----------

class DestinationListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, description="Recherche dans le nom et le pays"),
            OpenApiParameter("tag", str, description="Filtre exact, ex. Plage"),
            OpenApiParameter("ordering", str, description="name (défaut) ou popular"),
            OpenApiParameter("limit", int, description="1 à 100 (défaut 50)"),
        ],
        responses={200: OpenApiTypes.OBJECT},
        tags=["Destinations"],
    )
    def get(self, request):
        qs = Destination.objects

        q = request.query_params.get("q", "").strip()
        if q:
            qs = qs(Q(name__icontains=q) | Q(country__icontains=q))

        tag = request.query_params.get("tag", "").strip()
        if tag:
            qs = qs(tags=tag)

        destinations = list(qs.order_by("name"))
        counts = posts_counts(destinations)

        if request.query_params.get("ordering") == "popular":
            destinations.sort(key=lambda d: (-counts[d.slug], d.name))

        destinations = destinations[: _limit(request, 50, 100)]
        return Response([destination_data(d, counts[d.slug], request) for d in destinations])


class DestinationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["Destinations"])
    def get(self, request, slug):
        dest = _get_destination(slug)
        if not dest:
            return _not_found()
        count = Post.objects(destination__icontains=dest.name).count()
        return Response(destination_data(dest, count, request))


class DestinationPostsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("limit", int, description="1 à 50 (défaut 10)"),
            OpenApiParameter("before", str, description="Date ISO : posts plus anciens que"),
        ],
        responses={200: OpenApiTypes.OBJECT},
        tags=["Destinations"],
    )
    def get(self, request, slug):
        dest = _get_destination(slug)
        if not dest:
            return _not_found()

        me = request.user.user
        qs = Post.objects(destination__icontains=dest.name)

        before = request.query_params.get("before")
        if before:
            dt = parse_datetime(before)
            if dt is None:
                return Response({"error": "Paramètre 'before' invalide."},
                                status=status.HTTP_400_BAD_REQUEST)
            qs = qs(created_at__lt=dt)

        posts = list(qs.order_by("-created_at").limit(_limit(request, 10, 50)))
        return Response([post_data(p, me, request) for p in posts])
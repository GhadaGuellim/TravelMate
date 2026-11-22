from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from trips.models import Trip
from users.models import User

from .ai import generate_icebreaker
from .scoring import compatibility, interests


def to_int(value, default):
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return default


class MateSuggestionsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("limit", int, description="1 à 20 (défaut 5)"),
            OpenApiParameter("min_score", int, description="Score minimum, défaut 20"),
        ],
        responses={200: OpenApiTypes.OBJECT},
        tags=["Travel Mates"],
    )
    def get(self, request):
        me = request.user.user
        me.reload()
        today = date.today()
        limit = min(max(to_int(request.query_params.get("limit"), 5), 1), 20)
        min_score = to_int(request.query_params.get("min_score"), 20)

        my_trips = list(Trip.objects(owner=me, end_date__gte=today))
        needs = []
        if not interests(me):
            needs.append("preferences")
        if not my_trips:
            needs.append("trip")

        excluded = [me.id] + [getattr(u, "id", None) for u in (me.following or [])]
        candidates = list(User.objects(id__nin=excluded, role__ne="provider").limit(500))

        trips_by_owner = defaultdict(list)
        for t in Trip.objects(owner__in=[u.id for u in candidates], end_date__gte=today):
            trips_by_owner[t.to_mongo()["owner"]].append(t)

        results = []
        for u in candidates:
            c = compatibility(me, my_trips, u, trips_by_owner.get(u.id, []))
            if c["score"] < min_score:
                continue
            results.append({
                "id": str(u.id),
                "full_name": u.full_name,
                "avatar_url": u.avatar_url or "",
                "city": u.city or "",
                "country": u.country or "",
                **c,
            })

        results.sort(key=lambda r: (-r["score"], r["full_name"]))
        results = results[:limit]

        # IA : une phrase par suggestion affichée, en parallèle. Secours = phrase par règles.
        by_id = {str(u.id): u for u in candidates}

        def add_ai(r):
            try:
                return r, generate_icebreaker(
                    me, by_id[r["id"]], r["common_interests"], r["shared_trip"]
                )
            except Exception as e:
                print("IA ignorée :", repr(e))
                return r, None

        with ThreadPoolExecutor(max_workers=4) as pool:
            for r, text in pool.map(add_ai, results):
                if text:
                    r["icebreaker"] = text
                    r["icebreaker_source"] = "ai"

        return Response({"results": results, "needs": needs})
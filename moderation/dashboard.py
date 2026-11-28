from datetime import datetime, timedelta, timezone

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from mongoengine.base import get_document
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User

from .models import Report
from .permissions import IsAdmin

TAG = ["Modération"]


def model(name):
    """Retrouve un modèle par son nom de classe, sans connaître son app."""
    try:
        return get_document(name)
    except Exception:
        return None


def midnight(dt):
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def total(name, **filters):
    m = model(name)
    if m is None:
        return None
    try:
        return m.objects(**filters).count()
    except Exception:
        return None


def in_range(name, start, end=None):
    m = model(name)
    if m is None:
        return None
    flt = {"created_at__gte": start}
    if end:
        flt["created_at__lt"] = end
    try:
        return m.objects(**flt).count()
    except Exception:
        return None


def trend(name, days, today):
    """Période courante comparée à la précédente de même durée."""
    start = today - timedelta(days=days - 1)
    cur = in_range(name, start)
    if cur is None:
        return None
    prev = in_range(name, start - timedelta(days=days), start) or 0
    return {"current": cur, "previous": prev, "change": round((cur - prev) * 100 / prev) if prev else None}


def series(name, days, today):
    """Nombre d'éléments créés par jour."""
    start = today - timedelta(days=days - 1)
    labels = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
    counts = {}
    m = model(name)
    if m is not None:
        try:
            rows = m._get_collection().aggregate([
                {"$match": {"created_at": {"$gte": start}}},
                {"$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "n": {"$sum": 1},
                }},
            ])
            counts = {r["_id"]: r["n"] for r in rows}
        except Exception:
            pass
    return [{"date": d, "count": counts.get(d, 0)} for d in labels]


def group_by(name, field, match=None, limit=None, lower=False):
    m = model(name)
    if m is None:
        return []
    key = {"$toLower": f"${field}"} if lower else f"${field}"
    pipeline = [{"$match": match}] if match else []
    pipeline += [{"$group": {"_id": key, "n": {"$sum": 1}}}, {"$sort": {"n": -1}}]
    if limit:
        pipeline.append({"$limit": limit})
    try:
        return [(r["_id"], r["n"]) for r in m._get_collection().aggregate(pipeline)]
    except Exception:
        return []


def reviews_summary():
    m = model("Review")
    if m is None:
        return None
    try:
        rows = list(m._get_collection().aggregate([
            {"$group": {"_id": None, "n": {"$sum": 1}, "avg": {"$avg": "$rating"}}}
        ]))
        if not rows:
            return {"count": 0, "average": 0}
        return {"count": rows[0]["n"], "average": round(rows[0]["avg"] or 0, 2)}
    except Exception:
        return None


class DashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        parameters=[OpenApiParameter("days", int, description="7, 30 (défaut) ou 90")],
        responses={200: OpenApiTypes.OBJECT},
        tags=TAG,
    )
    def get(self, request):
        try:
            days = int(request.query_params.get("days", 30))
        except ValueError:
            days = 30
        if days not in (7, 30, 90):
            days = 30
        today = midnight(datetime.now(timezone.utc))

        roles = {"traveler": 0, "provider": 0, "admin": 0}
        for key, n in group_by("User", "role"):
            roles[key if key in roles else "traveler"] += n

        recent = User.objects.order_by("-created_at").limit(5)

        return Response({
            "days": days,
            "totals": {
                "users": User.objects.count(),
                "posts": total("Post"),
                "trips": total("Trip"),
                "bookings": total("Booking"),
                "communities": total("Community"),
                "itineraries": total("Itinerary"),
            },
            "trends": {name: trend(cls, days, today) for name, cls in
                       (("users", "User"), ("posts", "Post"), ("trips", "Trip"), ("bookings", "Booking"))},
            "series": {name: series(cls, days, today) for name, cls in
                       (("users", "User"), ("posts", "Post"), ("bookings", "Booking"))},
            "breakdown": {
                "roles": roles,
                "bookings_by_status": dict(group_by("Booking", "status")),
                "reports_by_reason": dict(group_by("Report", "reason")),
                "providers_by_type": {
                    (k or "autre"): n for k, n in
                    group_by("User", "service_type", match={"role": "provider"})
                },
            },
            "top_destinations": [
                {"name": k, "count": n} for k, n in
                group_by("Post", "destination", match={"destination": {"$nin": ["", None]}}, limit=5, lower=True)
            ],
            "reviews": reviews_summary(),
            "moderation": {
                "pending": Report.objects(status="pending").count(),
                "handled": Report.objects(status__ne="pending").count(),
                "suspended": User.objects(status="suspended").count(),
                "banned": User.objects(status="banned").count(),
            },
            "recent_users": [{
                "id": str(u.id),
                "full_name": u.full_name,
                "email": u.email,
                "role": u.role,
                "avatar_url": u.avatar_url or "",
                "created_at": u.created_at.isoformat() if u.created_at else None,
            } for u in recent],
        })
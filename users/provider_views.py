from datetime import date

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from mongoengine import Q
from mongoengine.errors import ValidationError as MongoValidationError
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from bookings.models import Booking

from .models import SERVICE_TYPES, User


def provider_data(u):
    """Fiche publique : ni e-mail ni téléphone (ils seront révélés après une réservation acceptée)."""
    today = date.today().isoformat()
    booked = [(b.start_date, b.end_date) for b in Booking.objects(provider=u, status="accepted")]
    return {
        "id": str(u.id),
        "full_name": u.full_name,
        "avatar_url": u.avatar_url or "",
        "bio": u.bio or "",
        "city": u.city or "",
        "country": u.country or "",
        "service_type": u.service_type,
        "service_description": u.service_description or "",
        "service_location": u.service_location or "",
        "daily_rate": u.daily_rate or 0,
        # on n'affiche que les périodes qui ne sont pas déjà terminées
        "availabilities": [p for p in (u.availabilities or []) if p.get("end", "") >= today],
        "booked": [{"start": s, "end": e} for s, e in booked],

    }


def get_int(request, name):
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return None
    try:
        return max(int(raw), 0)
    except ValueError:
        raise ValidationError({name: "Nombre entier attendu."})


def get_date(request, name):
    raw = request.query_params.get(name)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        raise ValidationError({name: "Date attendue au format AAAA-MM-JJ."})


class ProviderListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, description="Texte libre : nom, description, zone, ville"),
            OpenApiParameter("service_type", str, description="guide ou chauffeur"),
            OpenApiParameter("country", str),
            OpenApiParameter("city", str),
            OpenApiParameter("min_rate", int, description="Tarif/jour minimum (€)"),
            OpenApiParameter("max_rate", int, description="Tarif/jour maximum (€)"),
            OpenApiParameter("available_from", str, description="AAAA-MM-JJ"),
            OpenApiParameter("available_to", str, description="AAAA-MM-JJ (défaut : = available_from)"),
            OpenApiParameter("ordering", str, description="newest (défaut), rate_asc, rate_desc"),
            OpenApiParameter("limit", int, description="1 à 50 (défaut 20)"),
            OpenApiParameter("skip", int),
        ],
        responses={200: OpenApiTypes.OBJECT},
        tags=["Prestataires"],
    )
    def get(self, request):
        p = request.query_params
        qs = User.objects(role="provider", service_type__in=SERVICE_TYPES)

        q = p.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(full_name__icontains=q) | Q(service_description__icontains=q)
                | Q(service_location__icontains=q) | Q(city__icontains=q)
            )

        service_type = p.get("service_type", "").strip().lower()
        if service_type:
            if service_type not in SERVICE_TYPES:
                raise ValidationError({"service_type": "Valeurs possibles : guide, chauffeur."})
            qs = qs.filter(service_type=service_type)

        country = p.get("country", "").strip()
        if country:
            qs = qs.filter(country__icontains=country)

        city = p.get("city", "").strip()
        if city:
            # la ville peut être celle du profil ou la zone d'intervention (ex : "paris , marseille")
            qs = qs.filter(Q(city__icontains=city) | Q(service_location__icontains=city))

        min_rate, max_rate = get_int(request, "min_rate"), get_int(request, "max_rate")
        if min_rate is not None:
            qs = qs.filter(daily_rate__gte=min_rate)
        if max_rate is not None:
            qs = qs.filter(daily_rate__gt=0, daily_rate__lte=max_rate)

        ordering = {"rate_asc": "daily_rate", "rate_desc": "-daily_rate"}.get(p.get("ordering"), "-created_at")
        providers = list(qs.order_by(ordering))

        # disponibilité : une seule période du prestataire doit couvrir toute la demande
        start = get_date(request, "available_from")
        end = get_date(request, "available_to") or start
        if start:
            if end < start:
                raise ValidationError({"available_to": "La fin doit être après le début."})
            providers = [
                u for u in providers
                if any(a.get("start", "") <= start and a.get("end", "") >= end
                       for a in (u.availabilities or []))
            ]

        limit = min(max(get_int(request, "limit") or 20, 1), 50)
        skip = get_int(request, "skip") or 0
        return Response([provider_data(u) for u in providers[skip:skip + limit]])


class ProviderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["Prestataires"])
    def get(self, request, user_id):
        try:
            u = User.objects(id=user_id, role="provider").first()
        except MongoValidationError:
            u = None
        if not u:
            raise NotFound("Prestataire introuvable.")
        return Response(provider_data(u))
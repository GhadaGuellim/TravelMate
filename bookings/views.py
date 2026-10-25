from datetime import date

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from mongoengine.errors import ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User

from .models import Booking, now
from .serializers import BookingCreateSerializer, BookingRespondSerializer


def days_between(start, end):
    return (date.fromisoformat(end) - date.fromisoformat(start)).days + 1


def overlaps(a_start, a_end, b_start, b_end):
    return a_start <= b_end and b_start <= a_end


def person(u, with_phone=False):
    data = {
        "id": str(u.id),
        "full_name": u.full_name,
        "avatar_url": u.avatar_url or "",
        "city": u.city or "",
        "country": u.country or "",
    }
    if u.service_type:
        data["service_type"] = u.service_type
    if with_phone:
        data["phone"] = u.phone or ""
    return data


def booking_data(b, me):
    days = days_between(b.start_date, b.end_date)
    return {
        "id": str(b.id),
        "status": b.status,
        "start_date": b.start_date,
        "end_date": b.end_date,
        "days": days,
        "people": b.people,
        "message": b.message,
        "response_message": b.response_message,
        "daily_rate": b.daily_rate,
        "estimated_total": days * b.daily_rate,
        "provider": person(b.provider, with_phone=(b.status == "accepted" and b.traveler.id == me.id)),
        "traveler": person(b.traveler),
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "updated_at": b.updated_at.isoformat() if b.updated_at else None,
    }


def get_booking(booking_id):
    try:
        b = Booking.objects(id=booking_id).first()
    except MongoValidationError:
        b = None
    if not b:
        raise NotFound("Réservation introuvable.")
    return b


class BookingListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["Réservations"])
    def get(self, request):
        """role=sent (défaut, voyageur) ou role=received (prestataire)."""
        me = request.user.user
        if request.query_params.get("role") == "received":
            if me.role != "provider":
                raise PermissionDenied("Réservé aux prestataires.")
            qs = Booking.objects(provider=me)
        else:
            qs = Booking.objects(traveler=me)
        st = request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)
        return Response([booking_data(b, me) for b in qs.order_by("-created_at").limit(100)])

    @extend_schema(
        request=BookingCreateSerializer, responses={201: OpenApiTypes.OBJECT}, tags=["Réservations"]
    )
    def post(self, request):
        me = request.user.user
        if me.role == "provider":
            raise PermissionDenied("Un prestataire ne peut pas réserver un service.")

        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            provider = User.objects(id=d["provider_id"], role="provider").first()
        except MongoValidationError:
            provider = None
        if not provider or not provider.service_type:
            raise NotFound("Prestataire introuvable.")

        start, end = d["start_date"].isoformat(), d["end_date"].isoformat()
        if d["start_date"] < date.today():
            raise ValidationError({"start_date": "La date de début est déjà passée."})

        # 1) une période de disponibilité doit couvrir toute la demande
        if not any(a.get("start", "") <= start and a.get("end", "") >= end
                   for a in (provider.availabilities or [])):
            raise ValidationError("Le prestataire n'est pas disponible sur toute cette période.")

        # 2) pas de chevauchement avec une réservation déjà acceptée
        for other in Booking.objects(provider=provider, status="accepted"):
            if overlaps(start, end, other.start_date, other.end_date):
                raise ValidationError("Ces dates sont déjà réservées.")

        # 3) pas de doublon en attente
        for other in Booking.objects(traveler=me, provider=provider, status="pending"):
            if overlaps(start, end, other.start_date, other.end_date):
                raise ValidationError("Tu as déjà une demande en attente pour ces dates.")

        b = Booking(
            traveler=me, provider=provider, start_date=start, end_date=end,
            people=d["people"], message=d["message"], daily_rate=provider.daily_rate or 0,
        )
        b.save()
        return Response(booking_data(b, me), status=status.HTTP_201_CREATED)


class BookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["Réservations"])
    def get(self, request, booking_id):
        me = request.user.user
        b = get_booking(booking_id)
        if b.traveler.id != me.id and b.provider.id != me.id:
            raise PermissionDenied("Cette réservation ne te concerne pas.")
        return Response(booking_data(b, me))


class BookingCancelView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT}, tags=["Réservations"])
    def post(self, request, booking_id):
        me = request.user.user
        b = get_booking(booking_id)
        if b.traveler.id != me.id:
            raise PermissionDenied("Seul le voyageur peut annuler sa demande.")
        if b.status not in ("pending", "accepted"):
            raise ValidationError("Cette demande ne peut plus être annulée.")
        b.status = "cancelled"
        b.updated_at = now()
        b.save()
        return Response(booking_data(b, me))



class BookingRespondView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=BookingRespondSerializer, responses={200: OpenApiTypes.OBJECT}, tags=["Réservations"]
    )
    def post(self, request, booking_id):
        me = request.user.user
        b = get_booking(booking_id)
        if b.provider.id != me.id:
            raise PermissionDenied("Cette demande ne t'est pas adressée.")
        if b.status != "pending":
            raise ValidationError("Cette demande a déjà été traitée ou annulée.")

        serializer = BookingRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        if d["action"] == "accept":
            # on ne peut pas accepter deux demandes qui se chevauchent
            for other in Booking.objects(provider=me, status="accepted"):
                if overlaps(b.start_date, b.end_date, other.start_date, other.end_date):
                    raise ValidationError(
                        f"Conflit : tu as déjà accepté une réservation du "
                        f"{other.start_date} au {other.end_date}."
                    )
            b.status = "accepted"
        else:
            b.status = "refused"

        b.response_message = d["message"]
        b.updated_at = now()
        b.save()
        return Response(booking_data(b, me))
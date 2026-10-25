from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from mongoengine.errors import ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Day, Itinerary, Stop, now
from .serializers import ItinerarySerializer
from rest_framework.exceptions import ValidationError
from trips.models import Trip
import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework.parsers import FormParser, MultiPartParser

MAX_COVER = 5 * 1024 * 1024  # 5 Mo

def author_data(user):
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "avatar_url": user.avatar_url or "",
    }


def stop_data(s):
    return {
        "id": str(s.id),
        "title": s.title,
        "category": s.category,
        "time": s.time or "",
        "duration_min": s.duration_min,
        "lat": s.lat,
        "lng": s.lng,
        "cost": s.cost or 0,
        "status": s.status,
        "notes": s.notes or "",
    }


def itinerary_data(it, me):
    days = [{"title": d.title, "stops": [stop_data(s) for s in d.stops]} for d in it.days]
    trip = linked_trip(it)
    return {
        "id": str(it.id),
        "title": it.title,
        "destination": trip.destination if trip else it.destination,
        "description": it.description or "",
        "cover": it.cover or "",
        "start_date": (trip.start_date if trip else it.start_date).isoformat()
                      if (trip.start_date if trip else it.start_date) else None,
        "is_public": it.is_public,
        "is_mine": it.author.id == me.id,
        "author": author_data(it.author),
        "trip": {
            "id": str(trip.id),
            "title": trip.title,
            "start_date": trip.start_date.isoformat(),
            "end_date": trip.end_date.isoformat(),
            "budget": trip.budget or 0,
        } if trip else None,
        "days": days,
        "stops_count": sum(len(d["stops"]) for d in days),
        "budget": sum(s["cost"] for d in days for s in d["stops"]),
        "created_at": it.created_at.isoformat() if it.created_at else None,
        "updated_at": it.updated_at.isoformat() if it.updated_at else None,
    }


def build_days(days):
    return [
        Day(title=d["title"], stops=[Stop(**s) for s in d["stops"]])
        for d in days
    ]


def get_itinerary(itinerary_id, me, write=False):
    try:
        it = Itinerary.objects(id=itinerary_id).first()
    except MongoValidationError:
        it = None
    if not it:
        raise NotFound("Itinéraire introuvable.")
    mine = it.author.id == me.id
    if write and not mine:
        raise PermissionDenied("Ce n'est pas ton itinéraire.")
    if not mine and not it.is_public:
        trip = linked_trip(it)
        if not (trip and me in trip.participants):
            raise NotFound("Itinéraire introuvable.")
    return it


class ItineraryListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["Itinéraires"])
    def get(self, request):
        me = request.user.user
        if request.query_params.get("scope") == "public":
            qs = Itinerary.objects(is_public=True, author__ne=me)
            destination = request.query_params.get("destination")
            if destination:
                qs = qs.filter(destination__iexact=destination)
        else:
            qs = Itinerary.objects(author=me)
        limit = min(int(request.query_params.get("limit", 20)), 50)
        skip = int(request.query_params.get("skip", 0))
        items = qs.order_by("-created_at").skip(skip).limit(limit)
        return Response([itinerary_data(i, me) for i in items])

    @extend_schema(
        request=ItinerarySerializer, responses={201: OpenApiTypes.OBJECT}, tags=["Itinéraires"]
    )
    def post(self, request):
        me = request.user.user
        s = ItinerarySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        trip = None
        if d.get("trip"):
            trip = load_trip(d["trip"], me)
            if Itinerary.objects(trip=trip).first():
                raise ValidationError({"trip": "Ce voyage a déjà un itinéraire."})
        it = Itinerary(
            author=me,
            trip=trip,
            title=d["title"],
            destination=trip.destination if trip else d["destination"],
            description=d["description"],
            start_date=trip.start_date if trip else d.get("start_date"),
            is_public=d["is_public"],
            days=build_days(d["days"]),
        )
        it.save()
        return Response(itinerary_data(it, me), status=status.HTTP_201_CREATED)


class ItineraryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["Itinéraires"])
    def get(self, request, itinerary_id):
        me = request.user.user
        return Response(itinerary_data(get_itinerary(itinerary_id, me), me))

    @extend_schema(
        request=ItinerarySerializer, responses={200: OpenApiTypes.OBJECT}, tags=["Itinéraires"]
    )
    def put(self, request, itinerary_id):
        me = request.user.user
        it = get_itinerary(itinerary_id, me, write=True)
        s = ItinerarySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        it.title = d["title"]
        it.description = d["description"]
        it.is_public = d["is_public"]
        if not linked_trip(it):
            it.destination = d["destination"]
            it.start_date = d.get("start_date")
        it.days = build_days(d["days"])
        return Response(itinerary_data(it, me))

    @extend_schema(responses={204: None}, tags=["Itinéraires"])
    def delete(self, request, itinerary_id):
        it = get_itinerary(itinerary_id, request.user.user, write=True)
        it.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ItineraryCopyView(APIView):
    """POST = copie un itinéraire (le mien ou un public) dans mes itinéraires."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={201: OpenApiTypes.OBJECT}, tags=["Itinéraires"])
    def post(self, request, itinerary_id):
        me = request.user.user
        src = get_itinerary(itinerary_id, me)
        days = [
            Day(
                title=d.title,
                stops=[
                    Stop(
                        title=s.title,
                        category=s.category,
                        time=s.time,
                        duration_min=s.duration_min,
                        lat=s.lat,
                        lng=s.lng,
                        cost=s.cost,
                        notes=s.notes,
                        status="todo",  # la copie repart de zéro
                    )
                    for s in d.stops
                ],
            )
            for d in src.days
        ]
        it = Itinerary(
            author=me,
            cover=src.cover,
            title=src.title,
            destination=src.destination,
            description=src.description,
            start_date=None,
            is_public=False,
            days=days,
        )
        it.save()
        return Response(itinerary_data(it, me), status=status.HTTP_201_CREATED)


def load_trip(trip_id, me):
    try:
        trip = Trip.objects(id=trip_id).first()
    except MongoValidationError:
        trip = None
    if not trip:
        raise NotFound("Voyage introuvable.")
    if trip.owner.id != me.id:
        raise PermissionDenied("Ce n'est pas ton voyage.")
    return trip


def linked_trip(it):
    t = it.trip
    return t if t is not None and hasattr(t, "title") else None  # ignore les références cassées

class ItineraryByTripView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["Itinéraires"])
    def get(self, request, trip_id):
        me = request.user.user
        try:
            trip = Trip.objects(id=trip_id).first()
        except MongoValidationError:
            trip = None
        if not trip or not (trip.owner.id == me.id or me in trip.participants):
            raise NotFound("Voyage introuvable.")
        it = Itinerary.objects(trip=trip).first()
        if not it:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(itinerary_data(it, me))



class ItineraryCoverView(APIView):
    """POST (multipart, champ « image ») = définit la couverture. DELETE = la retire."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT}, tags=["Itinéraires"])
    def post(self, request, itinerary_id):
        me = request.user.user
        it = get_itinerary(itinerary_id, me, write=True)
        file = request.FILES.get("image")
        if not file:
            raise ValidationError({"image": "Aucune image envoyée."})
        if not (file.content_type or "").startswith("image/"):
            raise ValidationError({"image": "Le fichier doit être une image."})
        if file.size > MAX_COVER:
            raise ValidationError({"image": "Image trop lourde (5 Mo maximum)."})

        name = f"itineraries/{uuid.uuid4().hex}_{file.name}"
        path = default_storage.save(name, file)
        it.cover = request.build_absolute_uri(settings.MEDIA_URL + path)
        it.updated_at = now()
        it.save()
        return Response(itinerary_data(it, me))

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["Itinéraires"])
    def delete(self, request, itinerary_id):
        me = request.user.user
        it = get_itinerary(itinerary_id, me, write=True)
        it.cover = ""
        it.updated_at = now()
        it.save()
        return Response(itinerary_data(it, me))
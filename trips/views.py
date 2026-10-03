from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from mongoengine.errors import ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Trip
from .serializers import TripSerializer


def iso(value):
    return value.isoformat() if value else None


def trip_data(trip):
    return {
        "id": str(trip.id),
        "title": trip.title,
        "destination": trip.destination,
        "start_date": iso(trip.start_date),
        "end_date": iso(trip.end_date),
        "budget": trip.budget,
        "description": trip.description,
        "activities": list(trip.activities),
        "participants": [str(p.id) for p in trip.participants],
        "created_at": iso(trip.created_at),
    }


def find_trip(request, trip_id):
    """Retourne le voyage s'il appartient à l'utilisateur connecté, sinon None."""
    try:
        return Trip.objects(id=trip_id, owner=request.user.user).first()
    except MongoValidationError:
        return None


NOT_FOUND = {"error": "Voyage introuvable."}


class TripListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["Voyages"])
    def get(self, request):
        trips = Trip.objects(owner=request.user.user).order_by("-start_date")
        return Response([trip_data(t) for t in trips])

    @extend_schema(
        request=TripSerializer, responses={201: OpenApiTypes.OBJECT}, tags=["Voyages"]
    )
    def post(self, request):
        serializer = TripSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trip = Trip(owner=request.user.user, **serializer.validated_data)
        trip.save()
        return Response(trip_data(trip), status=status.HTTP_201_CREATED)


class TripDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["Voyages"])
    def get(self, request, trip_id):
        trip = find_trip(request, trip_id)
        if not trip:
            return Response(NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        return Response(trip_data(trip))

    @extend_schema(
        request=TripSerializer, responses={200: OpenApiTypes.OBJECT}, tags=["Voyages"]
    )
    def put(self, request, trip_id):
        trip = find_trip(request, trip_id)
        if not trip:
            return Response(NOT_FOUND, status=status.HTTP_404_NOT_FOUND)

        serializer = TripSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(trip, field, value)

        if trip.end_date < trip.start_date:
            return Response(
                {"error": "La date de fin doit être après la date de début."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        trip.save()
        return Response(trip_data(trip))

    @extend_schema(responses={204: None}, tags=["Voyages"])
    def delete(self, request, trip_id):
        trip = find_trip(request, trip_id)
        if not trip:
            return Response(NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        trip.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
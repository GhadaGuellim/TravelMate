from django.urls import path

from .views import ItineraryByTripView, ItineraryCopyView, ItineraryCoverView, ItineraryDetailView, ItineraryListCreateView

urlpatterns = [
    path("", ItineraryListCreateView.as_view()),
    path("by-trip/<str:trip_id>/", ItineraryByTripView.as_view()),
    path("<str:itinerary_id>/", ItineraryDetailView.as_view()),
    path("<str:itinerary_id>/copy/", ItineraryCopyView.as_view()),
    path("<str:itinerary_id>/cover/", ItineraryCoverView.as_view()),
]
from django.urls import path

from .views import TripDetailView, TripListView

urlpatterns = [
    path("", TripListView.as_view()),
    path("<str:trip_id>/", TripDetailView.as_view()),
]
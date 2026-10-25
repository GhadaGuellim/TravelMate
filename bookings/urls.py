from django.urls import path

from .views import BookingCancelView, BookingDetailView, BookingListCreateView, BookingRespondView

urlpatterns = [
    path("", BookingListCreateView.as_view()),
    path("<str:booking_id>/", BookingDetailView.as_view()),
    path("<str:booking_id>/cancel/", BookingCancelView.as_view()),
        path("<str:booking_id>/respond/", BookingRespondView.as_view()),
]
from django.urls import path

from .views import ReceivedReviewsView, ReviewDetailView, ReviewListCreateView

urlpatterns = [
    path("", ReviewListCreateView.as_view(), name="review-list-create"),
    path("received/", ReceivedReviewsView.as_view(), name="review-received"),
    path("<str:pk>/", ReviewDetailView.as_view(), name="review-detail"),
]
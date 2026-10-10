from django.urls import path

from .views import DestinationDetailView, DestinationListView, DestinationPostsView

urlpatterns = [
    path("", DestinationListView.as_view()),
    path("<slug:slug>/", DestinationDetailView.as_view()),
    path("<slug:slug>/posts/", DestinationPostsView.as_view()),
]
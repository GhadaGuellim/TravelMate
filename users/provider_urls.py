from django.urls import path

from .provider_views import ProviderDetailView, ProviderListView

urlpatterns = [
    path("", ProviderListView.as_view()),
    path("<str:user_id>/", ProviderDetailView.as_view()),
]
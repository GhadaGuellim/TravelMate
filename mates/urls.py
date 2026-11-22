from django.urls import path

from .views import MateSuggestionsView

urlpatterns = [
    path("suggestions/", MateSuggestionsView.as_view()),
]
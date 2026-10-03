from django.urls import path

from .views import PostCreateView

urlpatterns = [
    path("", PostCreateView.as_view()),
]
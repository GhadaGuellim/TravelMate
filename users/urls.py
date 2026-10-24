from django.urls import path

from .views import FollowView, LoginView, MeView, RegisterView, UserProfileView

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("me/", MeView.as_view()),
    path("<str:user_id>/profile/", UserProfileView.as_view()),   # US12
    path("<str:user_id>/follow/", FollowView.as_view()),          # US12
]
from django.urls import path

from .views import (
    AdminLoginView,
    FollowView,
    FollowingListView,
    LoginView,
    MeView,
    RegisterView,
    SuggestionsView,
    UserProfileView,
)

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("admin-login/", AdminLoginView.as_view()),
    path("me/", MeView.as_view()),
    path("<str:user_id>/profile/", UserProfileView.as_view()),
    path("<str:user_id>/follow/", FollowView.as_view()),
    path("following/", FollowingListView.as_view()),
    path("suggestions/", SuggestionsView.as_view()),
]
from django.urls import path

from .views import (
    CommunityDetailView,
    CommunityListView,
    JoinCommunityView,
    LeaveCommunityView,
    MyCommunitiesView,
)

urlpatterns = [
    path("", CommunityListView.as_view(), name="community-list"),
    path("mine/", MyCommunitiesView.as_view(), name="community-mine"),
    path("<str:pk>/", CommunityDetailView.as_view(), name="community-detail"),
    path("<str:pk>/join/", JoinCommunityView.as_view(), name="community-join"),
    path("<str:pk>/leave/", LeaveCommunityView.as_view(), name="community-leave"),
]
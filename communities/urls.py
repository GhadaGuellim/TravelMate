from django.urls import path

from .views import (
    CommentDetailView,
    CommentListCreateView,
    CommunityDetailView,
    CommunityListView,
    JoinCommunityView,
    LeaveCommunityView,
    MyCommunitiesView,
    PostDetailView,
    PostLikeView,
    PostListCreateView,
)

urlpatterns = [
    # Communautés (GET = liste, POST = création)
    path("", CommunityListView.as_view(), name="community-list"),
    path("mine/", MyCommunitiesView.as_view(), name="community-mine"),
    path("<str:pk>/", CommunityDetailView.as_view(), name="community-detail"),
    path("<str:pk>/join/", JoinCommunityView.as_view(), name="community-join"),
    path("<str:pk>/leave/", LeaveCommunityView.as_view(), name="community-leave"),
    # Publications
    path("<str:pk>/posts/", PostListCreateView.as_view(), name="post-list"),
    path("<str:pk>/posts/<str:post_id>/", PostDetailView.as_view(), name="post-detail"),
    path("<str:pk>/posts/<str:post_id>/like/", PostLikeView.as_view(), name="post-like"),
    # Commentaires
    path(
        "<str:pk>/posts/<str:post_id>/comments/",
        CommentListCreateView.as_view(),
        name="comment-list",
    ),
    path(
        "<str:pk>/posts/<str:post_id>/comments/<str:comment_id>/",
        CommentDetailView.as_view(),
        name="comment-detail",
    ),
]
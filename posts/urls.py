from django.urls import path

from .views import (
    CommentCreateView,
    CommentDeleteView,
    PostDetailView,
    PostLikeView,
    PostListCreateView,
    PostSaveView,
    SavedPostsView,
)

urlpatterns = [
    path("", PostListCreateView.as_view()),
    path("saved/", SavedPostsView.as_view()),
    path("<str:post_id>/", PostDetailView.as_view()),
    path("<str:post_id>/like/", PostLikeView.as_view()),
    path("<str:post_id>/save/", PostSaveView.as_view()),
    path("<str:post_id>/comments/", CommentCreateView.as_view()),
    path("<str:post_id>/comments/<str:comment_id>/", CommentDeleteView.as_view()),
]
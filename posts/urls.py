from django.urls import path

from .views import (
    CommentCreateView,
    CommentDeleteView,
    PostDetailView,
    PostLikeView,
    PostListCreateView,
    PostSaveView,
    PostShareView,
    SavedPostsView,
)

urlpatterns = [
    path("", PostListCreateView.as_view()),
    path("saved/", SavedPostsView.as_view()),
    path("<str:post_id>/", PostDetailView.as_view()),
    path("<str:post_id>/like/", PostLikeView.as_view()),
    path("<str:post_id>/save/", PostSaveView.as_view()),
    path("<str:post_id>/share/", PostShareView.as_view()),          # US11
    path("<str:post_id>/comments/", CommentCreateView.as_view()),
    path("<str:post_id>/comments/<str:comment_id>/", CommentDeleteView.as_view()),
]
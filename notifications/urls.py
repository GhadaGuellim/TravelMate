from django.urls import path

from .views import (
    MarkAllReadView,
    MarkReadView,
    NotificationDeleteView,
    NotificationListView,
    UnreadCountView,
)

urlpatterns = [
    path("", NotificationListView.as_view()),
    path("unread-count/", UnreadCountView.as_view()),
    path("read-all/", MarkAllReadView.as_view()),
    path("<str:notif_id>/read/", MarkReadView.as_view()),
    path("<str:notif_id>/", NotificationDeleteView.as_view()),
]
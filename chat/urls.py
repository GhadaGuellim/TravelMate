from django.urls import path

from .views import (
    ContactsView,
    ConversationListCreateView,
    GroupCreateView,
    GroupCreateView,
    GroupDetailView,
    GroupMemberView,
    GroupMembersView,
    MessageListCreateView,
    UnreadCountView,
)

urlpatterns = [
    path("contacts/", ContactsView.as_view()),
    path("unread/", UnreadCountView.as_view()),
    path("conversations/", ConversationListCreateView.as_view()),
    path("conversations/<str:conv_id>/messages/", MessageListCreateView.as_view()),
    path("groups/", GroupCreateView.as_view()),
    path("groups/<str:conv_id>/", GroupDetailView.as_view()),
    path("groups/<str:conv_id>/members/", GroupMembersView.as_view()),
    path("groups/<str:conv_id>/members/<str:user_id>/", GroupMemberView.as_view()),
]
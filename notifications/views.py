from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from mongoengine.errors import ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification


def notif_data(n):
    a = n.actor if hasattr(n.actor, "full_name") else None
    return {
        "id": str(n.id),
        "type": n.type,
        "text": n.text,
        "target": dict(n.target or {}),
        "read": n.read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "actor": {
            "id": str(a.id),
            "full_name": a.full_name,
            "avatar_url": a.avatar_url or "",
        } if a else None,
    }


def get_mine(me, notif_id):
    try:
        n = Notification.objects(id=notif_id, recipient=me).first()
    except MongoValidationError:
        n = None
    if not n:
        raise NotFound("Notification introuvable.")
    return n


def to_int(value, default):
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return default


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("unread", int, description="1 = non lues seulement"),
            OpenApiParameter("limit", int, description="1 à 50 (défaut 20)"),
            OpenApiParameter("skip", int),
        ],
        responses={200: OpenApiTypes.OBJECT},
        tags=["Notifications"],
    )
    def get(self, request):
        me = request.user.user
        qs = Notification.objects(recipient=me)
        if request.query_params.get("unread") == "1":
            qs = qs.filter(read=False)
        limit = min(max(to_int(request.query_params.get("limit"), 20), 1), 50)
        skip = to_int(request.query_params.get("skip"), 0)
        items = qs.order_by("-created_at").skip(skip).limit(limit)
        return Response([notif_data(n) for n in items])


class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["Notifications"])
    def get(self, request):
        me = request.user.user
        return Response({"count": Notification.objects(recipient=me, read=False).count()})


class MarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT}, tags=["Notifications"])
    def post(self, request):
        me = request.user.user
        Notification.objects(recipient=me, read=False).update(set__read=True)
        return Response({"count": 0})


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT}, tags=["Notifications"])
    def post(self, request, notif_id):
        n = get_mine(request.user.user, notif_id)
        if not n.read:
            n.update(set__read=True)
            n.reload()
        return Response(notif_data(n))


class NotificationDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={204: None}, tags=["Notifications"])
    def delete(self, request, notif_id):
        get_mine(request.user.user, notif_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
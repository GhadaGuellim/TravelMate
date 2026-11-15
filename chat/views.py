from django.shortcuts import render

from bson import ObjectId
from bson.errors import InvalidId
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from mongoengine.errors import NotUniqueError
from mongoengine.errors import ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User

from .models import Conversation, Message, now
from .serializers import (
    GroupCreateSerializer, GroupRenameSerializer, MembersSerializer,
    MessageSerializer, StartSerializer,
)
import uuid

TAG = ["Messagerie"]


# ---------- règles ----------

def follows(a, b):
    return any(getattr(u, "id", None) == b.id for u in a.following)


def can_message(me, other):
    if me.id == other.id:
        return False
    # Autorisé si l'un des deux suit l'autre.
    # Pour exiger un abonnement réciproque : return follows(me, other) and follows(other, me)
    return follows(me, other) or follows(other, me)


# ---------- helpers ----------

def iso(d):
    return d.isoformat() if d else None


def person_data(u):
    return {
        "id": str(u.id),
        "full_name": u.full_name,
        "avatar_url": u.avatar_url or "",
        "city": u.city or "",
        "country": u.country or "",
    }


def get_user(user_id):
    try:
        u = User.objects(id=user_id).first()
    except MongoValidationError:
        u = None
    if not u:
        raise NotFound("Voyageur introuvable.")
    return u


def pair_key(a, b):
    return ":".join(sorted([str(a.id), str(b.id)]))


def get_or_create_conversation(a, b):
    key = pair_key(a, b)
    conv = Conversation.objects(pair_key=key).first()
    if conv:
        return conv
    try:
        return Conversation(participants=[a, b], pair_key=key).save()
    except NotUniqueError:  # deux requêtes simultanées
        return Conversation.objects(pair_key=key).first()


def other_user(conv, me):
    return next((u for u in conv.participants if getattr(u, "id", None) != me.id), None)


def get_conversation(conv_id, me):
    try:
        conv = Conversation.objects(id=conv_id).first()
    except MongoValidationError:
        conv = None
    if not conv or not any(getattr(u, "id", None) == me.id for u in conv.participants):
        raise NotFound("Conversation introuvable.")
    return conv

MAX_MEMBERS = 20


def first_name(u):
    return (getattr(u, "full_name", "") or "").split(" ")[0]


def unread_qs(conv, me):
    return Message.objects(conversation=conv, sender__ne=me, read_at=None, read_by__ne=me)


def unread_count(conv, me):
    return unread_qs(conv, me).filter(system__ne=True).count()


def is_admin(conv, me):
    return getattr(conv.admin, "id", None) == me.id


def get_group(conv_id, me):
    conv = get_conversation(conv_id, me)
    if not conv.is_group:
        raise NotFound("Groupe introuvable.")
    return conv


def post_system(conv, actor, text):
    """Ajoute une ligne d'événement dans le fil du groupe."""
    msg = Message(conversation=conv, sender=actor, text=text, system=True).save()
    conv.update(
        set__last_message=text[:120],
        set__last_message_at=msg.created_at,
        set__last_sender=None,  # l'aperçu affiche juste le texte
    )


def conversation_data(conv, me):
    ls = conv.last_sender
    last_is_mine = bool(ls and getattr(ls, "id", None) == me.id)
    data = {
        "id": str(conv.id),
        "is_group": bool(conv.is_group),
        "last_message": conv.last_message or "",
        "last_message_at": iso(conv.last_message_at),
        "last_is_mine": last_is_mine,
        "unread": unread_count(conv, me),
    }
    if conv.is_group:
        data.update(
            name=conv.name,
            members=[person_data(u) for u in conv.participants if hasattr(u, "full_name")],
            is_admin=is_admin(conv, me),
            last_sender_name="" if last_is_mine or not hasattr(ls, "full_name") else first_name(ls),
            can_message=True,
        )
    else:
        other = other_user(conv, me)
        data.update(user=person_data(other), can_message=can_message(me, other))
    return data


def message_data(m, me):
    mine = m.sender.id == me.id
    data = {
        "id": str(m.id),
        "text": m.text,
        "created_at": iso(m.created_at),
        "is_mine": mine,
        "system": bool(m.system),
    }
    if not mine and hasattr(m.sender, "full_name"):
        data["sender"] = {
            "id": str(m.sender.id),
            "full_name": m.sender.full_name,
            "avatar_url": m.sender.avatar_url or "",
        }
    return data

# ---------- vues ----------

class ContactsView(APIView):
    """Voyageurs à qui je peux écrire : ceux que je suis + mes abonnés."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=TAG)
    def get(self, request):
        me = request.user.user
        me.reload()
        people = {u.id: u for u in me.following if hasattr(u, "full_name")}
        for u in User.objects(following=me):
            people[u.id] = u
        people.pop(me.id, None)
        data = sorted((person_data(u) for u in people.values()), key=lambda p: p["full_name"].lower())
        return Response(data)


class ConversationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=TAG)
    def get(self, request):
        me = request.user.user
        me.reload()
        convs = Conversation.objects(participants=me, last_message__ne="").order_by("-last_message_at")
        return Response([conversation_data(c, me) for c in convs if c.is_group or other_user(c, me)])
    
    @extend_schema(request=StartSerializer, responses={200: OpenApiTypes.OBJECT}, tags=TAG)
    def post(self, request):
        """Ouvre (ou crée) la conversation avec un voyageur."""
        me = request.user.user
        me.reload()
        s = StartSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        other = get_user(s.validated_data["user_id"])
        if not can_message(me, other):
            raise PermissionDenied("Tu dois suivre ce voyageur (ou être suivi par lui) pour lui écrire.")
        conv = get_or_create_conversation(me, other)
        return Response(conversation_data(conv, me))


class MessageListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=TAG)
    def get(self, request, conv_id):
        me = request.user.user
        conv = get_conversation(conv_id, me)

        after = request.query_params.get("after")
        qs = Message.objects(conversation=conv)
        if after:
            try:
                msgs = list(qs.filter(id__gt=ObjectId(after)).order_by("id"))
            except (InvalidId, MongoValidationError):
                raise ValidationError({"after": "Identifiant invalide."})
        else:
            msgs = list(qs.order_by("-id").limit(50))[::-1]

        # marquer comme lu
        if conv.is_group:
            unread_qs(conv, me).update(add_to_set__read_by=me)
        else:
            unread_qs(conv, me).update(set__read_at=now())

        seen_id = None
        if not conv.is_group:
            seen = Message.objects(conversation=conv, sender=me, read_at__ne=None).order_by("-id").first()
            seen_id = str(seen.id) if seen else None
        return Response({"messages": [message_data(m, me) for m in msgs], "seen_id": seen_id})

    @extend_schema(request=MessageSerializer, responses={201: OpenApiTypes.OBJECT}, tags=TAG)
    def post(self, request, conv_id):
        me = request.user.user
        me.reload()
        conv = get_conversation(conv_id, me)
        if not conv.is_group:
            other = other_user(conv, me)
            if not other or not can_message(me, other):
                raise PermissionDenied("Tu ne peux plus écrire à ce voyageur.")
        s = MessageSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        text = s.validated_data["text"]

        msg = Message(conversation=conv, sender=me, text=text).save()
        conv.update(
            set__last_message=text[:120],
            set__last_message_at=msg.created_at,
            set__last_sender=me,
        )
        return Response(message_data(msg, me), status=status.HTTP_201_CREATED)

class UnreadCountView(APIView):
    """Nombre total de messages non lus (pastille de la navbar)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=TAG)
    def get(self, request):
        me = request.user.user
        convs = list(Conversation.objects(participants=me))
        count = (
            Message.objects(
                conversation__in=convs, sender__ne=me, read_at=None, read_by__ne=me, system__ne=True
            ).count()
            if convs else 0
        )
        return Response({"count": count})


class GroupCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=GroupCreateSerializer, responses={201: OpenApiTypes.OBJECT}, tags=TAG)
    def post(self, request):
        me = request.user.user
        me.reload()
        s = GroupCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        ids = [i for i in dict.fromkeys(s.validated_data["members"]) if i != str(me.id)]
        if len(ids) < 2:
            raise ValidationError({"members": "Choisis au moins 2 autres voyageurs."})
        users = [get_user(i) for i in ids]
        for u in users:
            if not can_message(me, u):
                raise PermissionDenied(f"Tu ne peux pas ajouter {u.full_name} : abonnement requis.")

        conv = Conversation(
            participants=[me, *users],
            pair_key=f"group:{uuid.uuid4().hex}",
            is_group=True,
            name=s.validated_data["name"],
            admin=me,
        ).save()
        post_system(conv, me, f"{first_name(me)} a créé le groupe")
        conv.reload()
        return Response(conversation_data(conv, me), status=status.HTTP_201_CREATED)


class GroupDetailView(APIView):
    """PATCH = renommer (admin)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=GroupRenameSerializer, responses={200: OpenApiTypes.OBJECT}, tags=TAG)
    def patch(self, request, conv_id):
        me = request.user.user
        conv = get_group(conv_id, me)
        if not is_admin(conv, me):
            raise PermissionDenied("Seul l'admin peut renommer le groupe.")
        s = GroupRenameSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        conv.update(set__name=s.validated_data["name"])
        conv.reload()
        post_system(conv, me, f"{first_name(me)} a renommé le groupe « {conv.name} »")
        conv.reload()
        return Response(conversation_data(conv, me))


class GroupMembersView(APIView):
    """POST = ajouter des membres (admin)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=MembersSerializer, responses={200: OpenApiTypes.OBJECT}, tags=TAG)
    def post(self, request, conv_id):
        me = request.user.user
        me.reload()
        conv = get_group(conv_id, me)
        if not is_admin(conv, me):
            raise PermissionDenied("Seul l'admin peut ajouter des membres.")
        s = MembersSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        current = {getattr(u, "id", None) for u in conv.participants}
        new = []
        for uid in dict.fromkeys(s.validated_data["user_ids"]):
            u = get_user(uid)
            if u.id in current:
                continue
            if not can_message(me, u):
                raise PermissionDenied(f"Tu ne peux pas ajouter {u.full_name} : abonnement requis.")
            new.append(u)
        if len(current) + len(new) > MAX_MEMBERS:
            raise ValidationError({"user_ids": f"{MAX_MEMBERS} membres maximum."})

        for u in new:
            conv.update(add_to_set__participants=u)
        if new:
            post_system(conv, me, f"{first_name(me)} a ajouté {', '.join(first_name(u) for u in new)}")
        conv.reload()
        return Response(conversation_data(conv, me))


class GroupMemberView(APIView):
    """DELETE = retirer un membre (admin) ou quitter le groupe (user_id = « me » ou son propre id)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT, 204: None}, tags=TAG)
    def delete(self, request, conv_id, user_id):
        me = request.user.user
        conv = get_group(conv_id, me)
        leaving = user_id in ("me", str(me.id))
        admin = is_admin(conv, me)
        if not leaving and not admin:
            raise PermissionDenied("Seul l'admin peut retirer un membre.")

        target_id = str(me.id) if leaving else user_id
        target = next((u for u in conv.participants if str(getattr(u, "id", "")) == target_id), None)
        if not target:
            raise NotFound("Ce voyageur n'est pas dans le groupe.")

        conv.update(pull__participants=target)
        conv.reload()
        remaining = [u for u in conv.participants if hasattr(u, "full_name")]

        if len(remaining) < 2:  # plus assez de monde : on supprime le groupe
            Message.objects(conversation=conv).delete()
            conv.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        if leaving and admin:  # l'admin part : le groupe passe au membre suivant
            conv.update(set__admin=remaining[0])

        text = (
            f"{first_name(me)} a quitté le groupe"
            if leaving else f"{first_name(me)} a retiré {first_name(target)}"
        )
        post_system(conv, me, text)
        if leaving:
            return Response(status=status.HTTP_204_NO_CONTENT)
        conv.reload()
        return Response(conversation_data(conv, me))
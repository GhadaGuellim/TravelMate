from django.db import models


def now():
    return datetime.now(timezone.utc)


from datetime import datetime, timezone

from mongoengine import (
    CASCADE,
    PULL,
    BooleanField,
    DateTimeField,
    Document,
    ListField,
    ReferenceField,
    StringField,
)

from users.models import User



class Conversation(Document):
    participants = ListField(ReferenceField(User, reverse_delete_rule=PULL))
    # 1-1 : "idA:idB" trié. Groupe : "group:<uuid>" (donc toujours unique)
    pair_key = StringField(required=True, unique=True)
    is_group = BooleanField(default=False)
    name = StringField(max_length=60, default="")
    admin = ReferenceField(User)
    last_message = StringField(default="", max_length=200)
    last_message_at = DateTimeField(default=now)
    last_sender = ReferenceField(User)
    created_at = DateTimeField(default=now)

    meta = {"collection": "conversations", "indexes": ["participants", "-last_message_at"]}


class Message(Document):
    conversation = ReferenceField(Conversation, required=True, reverse_delete_rule=CASCADE)
    sender = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    text = StringField(required=True, max_length=2000)
    created_at = DateTimeField(default=now)
    read_at = DateTimeField()                      # conversations à deux : None = non lu
    read_by = ListField(ReferenceField(User))      # groupes : qui a lu
    system = BooleanField(default=False)           # « X a ajouté Y »

    meta = {"collection": "messages", "indexes": [{"fields": ["conversation", "-id"]}]}
from datetime import datetime, timezone

from mongoengine import (
    CASCADE,
    BooleanField,
    DateTimeField,
    DictField,
    Document,
    ReferenceField,
    StringField,
)

from users.models import User

TYPES = (
    "like", "comment", "follow",
    "booking_request", "booking_accepted", "booking_refused", "booking_cancelled",
    "message", "group", "moderation", 
)


def now():
    return datetime.now(timezone.utc)


class Notification(Document):
    recipient = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    actor = ReferenceField(User, reverse_delete_rule=CASCADE)
    type = StringField(choices=TYPES, required=True)
    text = StringField(required=True, max_length=300)
    target = DictField()  # ex : {"section": "requests", "id": "..."}
    read = BooleanField(default=False)
    created_at = DateTimeField(default=now)

    meta = {
        "collection": "notifications",
        "indexes": [("recipient", "read"), "-created_at"],
    }
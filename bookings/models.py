from datetime import datetime, timezone

from mongoengine import (
    CASCADE,
    DateTimeField,
    Document,
    IntField,
    ReferenceField,
    StringField,
)

from users.models import User

STATUSES = ("pending", "accepted", "refused", "cancelled")


def now():
    return datetime.now(timezone.utc)


class Booking(Document):
    traveler = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    provider = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    start_date = StringField(required=True)  # AAAA-MM-JJ
    end_date = StringField(required=True)
    people = IntField(default=1, min_value=1, max_value=50)
    message = StringField(default="", max_length=1000)
    status = StringField(choices=STATUSES, default="pending")
    response_message = StringField(default="", max_length=500)
    daily_rate = IntField(default=0)  # tarif figé au moment de la demande
    created_at = DateTimeField(default=now)
    updated_at = DateTimeField()

    meta = {
        "collection": "bookings",
        "indexes": ["traveler", "provider", "status", "-created_at"],
    }
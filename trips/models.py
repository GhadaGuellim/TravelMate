from datetime import datetime, timezone

from mongoengine import (
    CASCADE,
    DateField,
    DateTimeField,
    Document,
    FloatField,
    ListField,
    ReferenceField,
    StringField,
)

from users.models import User


class Trip(Document):
    owner = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    title = StringField(required=True, max_length=100)
    destination = StringField(required=True, max_length=100)
    start_date = DateField(required=True)
    end_date = DateField(required=True)
    budget = FloatField(default=0, min_value=0)
    description = StringField(default="")
    activities = ListField(StringField(max_length=200), default=list)
    participants = ListField(ReferenceField(User), default=list)
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))

    meta = {"collection": "trips", "indexes": ["owner"]}
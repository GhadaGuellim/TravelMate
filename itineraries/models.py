from datetime import datetime, timezone

from bson import ObjectId
from mongoengine import (
    CASCADE,
    BooleanField,
    DateField,
    DateTimeField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentField,
    FloatField,
    IntField,
    ListField,
    ObjectIdField,
    ReferenceField,
    StringField,
)

from trips.models import Trip
from users.models import User

CATEGORIES = ["food", "sight", "nature", "stay", "transport", "other"]
STATUSES = ["todo", "booked", "done"]


def now():
    return datetime.now(timezone.utc)


class Stop(EmbeddedDocument):
    id = ObjectIdField(default=ObjectId)
    title = StringField(required=True, max_length=120)
    category = StringField(choices=CATEGORIES, default="other")
    time = StringField(max_length=5, default="")  # "09:30"
    duration_min = IntField(min_value=0)
    lat = FloatField(min_value=-90, max_value=90)
    lng = FloatField(min_value=-180, max_value=180)
    cost = FloatField(default=0, min_value=0)
    status = StringField(choices=STATUSES, default="todo")
    notes = StringField(max_length=500, default="")


class Day(EmbeddedDocument):
    title = StringField(max_length=100, default="")
    stops = ListField(EmbeddedDocumentField(Stop))


class Itinerary(Document):
    author = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    title = StringField(required=True, max_length=120)
    destination = StringField(required=True, max_length=100)
    description = StringField(default="", max_length=1000)
    start_date = DateField()
    days = ListField(EmbeddedDocumentField(Day))
    is_public = BooleanField(default=False)
    created_at = DateTimeField(default=now)
    updated_at = DateTimeField()

    trip = ReferenceField(Trip, reverse_delete_rule=CASCADE)  # optionnel
    cover = StringField(default="")
    meta = {
        "collection": "itineraries",
        "indexes": [
            "author", "-created_at", "is_public", "destination",
            {"fields": ["trip"], "unique": True, "sparse": True},  # 1 itinéraire max par voyage
        ],
    }
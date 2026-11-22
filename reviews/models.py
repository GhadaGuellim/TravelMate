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

# si c'est un tuple de textes
TARGET_TYPES = ("provider", "trip", "place")

# si c'est une liste de couples (valeur, libellé)
TARGET_TYPES = (("provider", "Prestataire"), ("trip", "Voyage"), ("place", "Lieu"))

class Review(Document):
    author = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    target_type = StringField(required=True, choices=TARGET_TYPES)
    target_id = StringField(required=True, max_length=100)
    rating = IntField(required=True, min_value=1, max_value=5)
    comment = StringField(default="", max_length=1000)
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))
    updated_at = DateTimeField(default=lambda: datetime.now(timezone.utc))

    meta = {
        "collection": "reviews",
        "indexes": [
            {"fields": ["author", "target_type", "target_id"], "unique": True},
            ["target_type", "target_id"],
        ],
    }
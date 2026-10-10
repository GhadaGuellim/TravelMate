from datetime import datetime, timezone

from bson import ObjectId
from mongoengine import (
    CASCADE,
    DateTimeField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentField,
    ListField,
    ObjectIdField,
    ReferenceField,
    StringField,
)

from users.models import User


def now():
    return datetime.now(timezone.utc)


class Comment(EmbeddedDocument):
    id = ObjectIdField(default=ObjectId)
    author = ReferenceField(User, required=True)
    text = StringField(required=True, max_length=500)
    created_at = DateTimeField(default=now)


class Post(Document):
    author = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    text = StringField(required=True, max_length=1000)
    destination = StringField(default="", max_length=100)
    image = StringField(default="")  # URL de l'image
    likes = ListField(ReferenceField(User))
    saved_by = ListField(ReferenceField(User))
    comments = ListField(EmbeddedDocumentField(Comment))
    created_at = DateTimeField(default=now)
    updated_at = DateTimeField()

    meta = {"collection": "posts", "indexes": ["author", "-created_at", "destination"]}
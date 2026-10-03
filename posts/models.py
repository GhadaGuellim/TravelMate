from datetime import datetime, timezone

from mongoengine import (
    CASCADE,
    DateTimeField,
    Document,
    ReferenceField,
    StringField,
)

from users.models import User


class Post(Document):
    author = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    text = StringField(required=True, max_length=1000)
    destination = StringField(default="", max_length=100)
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))

    meta = {"collection": "posts", "indexes": ["author", "-created_at"]}
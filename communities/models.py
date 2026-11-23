from datetime import datetime, timezone

from mongoengine import DateTimeField, Document, ListField, ReferenceField, StringField


class Community(Document):
    name = StringField(required=True, unique=True, max_length=100)
    description = StringField(max_length=500)
    cover_image = StringField(max_length=500)
    topics = ListField(StringField(max_length=50))
    members = ListField(ReferenceField("User"))
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))

    meta = {"collection": "communities"}
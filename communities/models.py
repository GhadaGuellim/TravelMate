from datetime import datetime, timezone

from mongoengine import (
    CASCADE,
    DateTimeField,
    Document,
    ListField,
    ObjectIdField,
    ReferenceField,
    StringField,
)


def utcnow():
    return datetime.now(timezone.utc)


class Community(Document):
    name = StringField(required=True, unique=True, max_length=100)
    description = StringField(max_length=500)
    cover_image = StringField(max_length=500)
    topics = ListField(StringField(max_length=50))
    members = ListField(ReferenceField("User"))
    created_by = ReferenceField("User")  # None pour les communautés prédéfinies
    created_at = DateTimeField(default=utcnow)

    meta = {"collection": "communities"}


class CommunityPost(Document):
    community = ReferenceField("Community", required=True, reverse_delete_rule=CASCADE)
    author = ReferenceField("User", required=True, reverse_delete_rule=CASCADE)
    content = StringField(required=True, max_length=2000)
    image = StringField()  # data URL (image envoyée depuis l'ordinateur)
    likes = ListField(ObjectIdField())  # ids des utilisateurs qui aiment
    created_at = DateTimeField(default=utcnow)

    meta = {
        "collection": "community_posts",
        "indexes": ["community", "-created_at"],
        "ordering": ["-created_at"],
    }


class CommunityComment(Document):
    post = ReferenceField("CommunityPost", required=True, reverse_delete_rule=CASCADE)
    author = ReferenceField("User", required=True, reverse_delete_rule=CASCADE)
    content = StringField(required=True, max_length=1000)
    created_at = DateTimeField(default=utcnow)

    meta = {
        "collection": "community_comments",
        "indexes": ["post", "created_at"],
        "ordering": ["created_at"],
    }
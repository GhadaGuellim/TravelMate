from datetime import datetime, timezone

from mongoengine import (
    CASCADE, NULLIFY, DateTimeField, Document, ReferenceField, StringField,
)

from users.models import User

TARGET_TYPES = ("post", "comment", "review", "user")
REASONS = ("spam", "harassment", "hate", "inappropriate", "scam", "other")
STATUSES = ("pending", "resolved", "dismissed")


def now():
    return datetime.now(timezone.utc)


class Report(Document):
    reporter = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    target_type = StringField(choices=TARGET_TYPES, required=True)
    target_id = StringField(required=True, max_length=100)  # commentaire : "<id post>:<id commentaire>"
    target_owner = ReferenceField(User, reverse_delete_rule=NULLIFY)
    reason = StringField(choices=REASONS, required=True)
    details = StringField(default="", max_length=500)
    snapshot = StringField(default="", max_length=400)  # extrait conservé même si le contenu est supprimé
    status = StringField(choices=STATUSES, default="pending")
    resolution = StringField(default="", max_length=300)
    handled_by = ReferenceField(User, reverse_delete_rule=NULLIFY)
    handled_at = DateTimeField()
    created_at = DateTimeField(default=now)

    meta = {
        "collection": "reports",
        "indexes": ["status", ("target_type", "target_id"), "-created_at"],
    }


class ModerationLog(Document):
    admin = ReferenceField(User, reverse_delete_rule=NULLIFY)
    action = StringField(required=True, max_length=40)
    target_user = ReferenceField(User, reverse_delete_rule=NULLIFY)
    target_label = StringField(default="", max_length=200)
    note = StringField(default="", max_length=300)
    created_at = DateTimeField(default=now)

    meta = {"collection": "moderation_log", "indexes": ["-created_at"]}
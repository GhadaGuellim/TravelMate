from datetime import datetime, timezone

from django.contrib.auth.hashers import check_password, make_password
from mongoengine import DateTimeField, Document, EmailField, ListField, ReferenceField, StringField
ROLES = ("traveler", "provider")
SERVICE_TYPES = ("guide", "chauffeur")

class User(Document):
    email = EmailField(required=True, unique=True)
    full_name = StringField(required=True, max_length=100)
    password = StringField(required=True)
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))

    bio = StringField(max_length=500)
    city = StringField(max_length=100)
    country = StringField(max_length=100)
    preferences = StringField(max_length=500)
    avatar_url = StringField(max_length=200000)
    role = StringField(choices=ROLES, default="traveler")
    # US12 : liste des voyageurs suivis
    following = ListField(ReferenceField("self"))
    service_type = StringField(choices=SERVICE_TYPES)
    service_description = StringField(max_length=1000)
    service_location = StringField(max_length=200)
    phone = StringField(max_length=30)
    meta = {"collection": "users"}

    @property
    def is_provider(self):
        return self.role == "provider"

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def verify_password(self, raw_password):
        return check_password(raw_password, self.password)
from django.db import models

# Create your models here.
from datetime import datetime, timezone

from mongoengine import DateTimeField, Document, IntField, ListField, StringField


class Destination(Document):
    slug = StringField(required=True, unique=True, max_length=100)  # "tokyo", "new-york"
    name = StringField(required=True, max_length=100)
    country = StringField(required=True, max_length=100)
    description = StringField(default="", max_length=2000)
    # chemin relatif dans MEDIA_ROOT ("destinations/tokyo.jpg") ou URL complète
    cover = StringField(default="")
    best_season = StringField(default="", max_length=80)
    # budget indicatif en euros pour une semaine, hors vol
    avg_budget = IntField(default=0, min_value=0)
    tags = ListField(StringField(max_length=30))
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))

    meta = {"collection": "destinations", "indexes": ["name", "country", "tags"]}

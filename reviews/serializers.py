from rest_framework import serializers

from .models import TARGET_TYPES


class ReviewSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    target_type = serializers.ChoiceField(choices=TARGET_TYPES)
    target_id = serializers.CharField(max_length=100)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(
        max_length=1000, required=False, allow_blank=True, default=""
    )
    author_id = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()
    author_avatar = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_author_id(self, obj):
        return str(obj.author.id)

    def get_author_name(self, obj):
        for field in ("full_name", "username", "name", "first_name", "email"):
            value = getattr(obj.author, field, None)
            if value:
                return value
        return ""

    def get_author_avatar(self, obj):
        return getattr(obj.author, "avatar_url", "") or ""
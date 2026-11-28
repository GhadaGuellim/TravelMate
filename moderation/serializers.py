from rest_framework import serializers

from .models import REASONS, TARGET_TYPES


class ReportCreateSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=TARGET_TYPES)
    target_id = serializers.CharField(max_length=100)
    reason = serializers.ChoiceField(choices=REASONS)
    details = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class ResolveSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["dismiss", "apply"])
    delete_content = serializers.BooleanField(default=False)
    sanction = serializers.ChoiceField(choices=["none", "suspend", "ban"], default="none")
    days = serializers.IntegerField(min_value=1, max_value=365, default=7)
    note = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class UserStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["active", "suspended", "banned"])
    days = serializers.IntegerField(min_value=1, max_value=365, default=7)
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")
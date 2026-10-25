from rest_framework import serializers

from .models import CATEGORIES, STATUSES


class StopSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    category = serializers.ChoiceField(choices=CATEGORIES, default="other")
    time = serializers.CharField(max_length=5, allow_blank=True, default="")
    duration_min = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    lat = serializers.FloatField(min_value=-90, max_value=90, required=False, allow_null=True)
    lng = serializers.FloatField(min_value=-180, max_value=180, required=False, allow_null=True)
    cost = serializers.FloatField(min_value=0, default=0)
    status = serializers.ChoiceField(choices=STATUSES, default="todo")
    notes = serializers.CharField(max_length=500, allow_blank=True, default="")


class DaySerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100, allow_blank=True, default="")
    stops = StopSerializer(many=True, default=list)

    def validate_stops(self, value):
        if len(value) > 30:
            raise serializers.ValidationError("30 étapes maximum par jour.")
        return value


class ItinerarySerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    destination = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=1000, allow_blank=True, default="")
    start_date = serializers.DateField(required=False, allow_null=True)
    is_public = serializers.BooleanField(default=False)
    days = DaySerializer(many=True, default=list)
    trip = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    def validate_days(self, value):
        if len(value) > 30:
            raise serializers.ValidationError("30 jours maximum.")
        return value
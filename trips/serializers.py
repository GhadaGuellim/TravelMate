from rest_framework import serializers


class TripSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100)
    destination = serializers.CharField(max_length=100)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    budget = serializers.FloatField(min_value=0, required=False, default=0)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    activities = serializers.ListField(
        child=serializers.CharField(max_length=200), required=False, default=list
    )

    def validate(self, attrs):
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        if start and end and end < start:
            raise serializers.ValidationError(
                "La date de fin doit être après la date de début."
            )
        return attrs
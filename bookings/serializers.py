from rest_framework import serializers


class BookingCreateSerializer(serializers.Serializer):
    provider_id = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    people = serializers.IntegerField(min_value=1, max_value=50, default=1)
    message = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")

    def validate(self, data):
        if data["end_date"] < data["start_date"]:
            raise serializers.ValidationError("La date de fin doit être après la date de début.")
        return data


class BookingRespondSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "refuse"])
    message = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


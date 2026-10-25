from rest_framework import serializers

SERVICE_TYPES = ("guide", "chauffeur")
ROLES = ("traveler", "provider")


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=100)
    password = serializers.CharField(min_length=8, write_only=True)
    role = serializers.ChoiceField(choices=ROLES, default="traveler")


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class PeriodSerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()

    def validate(self, data):
        if data["end"] < data["start"]:
            raise serializers.ValidationError("La date de fin doit être après la date de début.")
        return data


class ProfileUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=100, required=False)
    bio = serializers.CharField(max_length=500, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False, allow_blank=True)
    preferences = serializers.CharField(max_length=500, required=False, allow_blank=True)
    avatar_url = serializers.CharField(max_length=200000, required=False, allow_blank=True)

    service_type = serializers.ChoiceField(choices=SERVICE_TYPES, required=False, allow_blank=True)
    service_description = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    service_location = serializers.CharField(max_length=200, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    daily_rate = serializers.IntegerField(min_value=0, max_value=100000, required=False)
    availabilities = PeriodSerializer(many=True, required=False)

    def validate_availabilities(self, periods):
        if len(periods) > 20:
            raise serializers.ValidationError("20 périodes maximum.")
        # stockage en texte ISO (AAAA-MM-JJ), trié par date de début
        return sorted(
            ({"start": p["start"].isoformat(), "end": p["end"].isoformat()} for p in periods),
            key=lambda p: p["start"],
        )
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
from rest_framework import serializers


class PostSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=1000)
    destination = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
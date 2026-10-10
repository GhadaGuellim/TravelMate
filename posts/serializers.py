from rest_framework import serializers


class PostSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=1000)
    destination = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
    image = serializers.ImageField(required=False)


class PostUpdateSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=1000, required=False)
    destination = serializers.CharField(max_length=100, required=False, allow_blank=True)


class CommentSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=500)
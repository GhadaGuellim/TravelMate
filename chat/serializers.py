from rest_framework import serializers


class StartSerializer(serializers.Serializer):
    user_id = serializers.CharField()


class MessageSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2000)  # refuse le texte vide ou fait d'espaces


class GroupCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=60)
    members = serializers.ListField(child=serializers.CharField(), min_length=2, max_length=19)


class GroupRenameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=60)


class MembersSerializer(serializers.Serializer):
    user_ids = serializers.ListField(child=serializers.CharField(), min_length=1, max_length=19)
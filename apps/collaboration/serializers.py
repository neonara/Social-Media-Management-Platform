from rest_framework import serializers
from .models import ChatRoom, Message
from django.contrib.auth import get_user_model

User = get_user_model()


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)
    sender_email = serializers.EmailField(source="sender.email", read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "content",
            "sender",
            "sender_name",
            "sender_email",
            "created_at",
            "is_read",
            "read_at",
        ]
        read_only_fields = ["id", "sender", "created_at", "is_read", "read_at"]


class ChatRoomSerializer(serializers.ModelSerializer):
    members = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True)
    member_details = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            "id",
            "name",
            "room_type",
            "members",
            "member_details",
            "created_at",
            "created_by",
            "is_active",
            "last_message",
            "unread_count",
        ]
        read_only_fields = ["id", "created_at", "created_by"]

    def get_member_details(self, obj):
        return [
            {
                "id": member.id,
                "name": member.get_full_name() or member.email,
                "email": member.email,
            }
            for member in obj.members.all()
        ]

    def get_last_message(self, obj):
        last_msg = obj.messages.order_by("-created_at").first()
        if last_msg:
            return MessageSerializer(last_msg).data
        return None

    def get_unread_count(self, obj):
        user = self.context.get("request").user
        if user.is_authenticated:
            return obj.messages.filter(is_read=False).exclude(sender=user).count()
        return 0


class ChatRoomCreateSerializer(serializers.ModelSerializer):
    members = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True)

    class Meta:
        model = ChatRoom
        fields = ["name", "room_type", "members"]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

from rest_framework import serializers
from .models import SocialPage


class SocialPageSerializer(serializers.ModelSerializer):
    # Add a connected field to indicate the page is active
    connected = serializers.SerializerMethodField()
    token_valid = serializers.SerializerMethodField()

    class Meta:
        model = SocialPage
        fields = [
            "id",
            "platform",
            "client",
            "page_id",
            "page_name",
            "connected",
            "token_valid",
            "created_at",
            "updated_at",
        ]

    def get_connected(self, obj):
        # A SocialPage object exists, so it's connected
        return True

    def get_token_valid(self, obj):
        # Check if the token is still valid
        return obj.is_token_valid()

from rest_framework import serializers
from .models import SocialPage

class SocialPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialPage
        fields = '__all__'

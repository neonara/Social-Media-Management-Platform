from rest_framework import serializers
from apps.content.models import Post
from .models import EngagementForecast, TrainingData, ModelMetrics


class EngagementForecastSerializer(serializers.ModelSerializer):
    post_title = serializers.CharField(source='post.title', read_only=True)
    post_id = serializers.IntegerField(source='post.id', read_only=True)
    
    class Meta:
        model = EngagementForecast
        fields = [
            'id',
            'post_id',
            'post_title',
            'caption_length',
            'hashtag_count',
            'time_of_day',
            'day_of_week',
            'platform',
            'media_type',
            'brand_sentiment',
            'predicted_engagement_score',
            'engagement_level',
            'confidence_score',
            'actual_engagement_score',
            'actual_engagement_level',
            'predicted_at',
            'updated_at',
        ]
        read_only_fields = [
            'predicted_engagement_score',
            'engagement_level',
            'confidence_score',
            'predicted_at',
            'updated_at',
        ]


class EngagementPredictionRequestSerializer(serializers.Serializer):
    """
    Serializer for engagement prediction requests.
    """
    post_id = serializers.IntegerField(required=False)
    caption = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    caption_length = serializers.IntegerField(min_value=0, max_value=10000)
    hashtag_count = serializers.IntegerField(min_value=0, max_value=100)
    time_of_day = serializers.CharField(max_length=5)  # "HH:MM" format
    day_of_week = serializers.IntegerField(min_value=0, max_value=6)
    platform = serializers.ChoiceField(choices=['facebook', 'instagram', 'linkedin'])
    media_type = serializers.ChoiceField(choices=['image', 'video', 'carousel', 'text'])
    brand_sentiment = serializers.FloatField(min_value=0.0, max_value=1.0, default=0.5)


class EngagementPredictionResponseSerializer(serializers.Serializer):
    """
    Serializer for engagement prediction responses.
    """
    predicted_engagement_score = serializers.FloatField()
    engagement_level = serializers.CharField()
    confidence_score = serializers.FloatField()
    reasoning = serializers.CharField(required=False)
    top_factors = serializers.ListField(child=serializers.CharField(), required=False)
    improvements = serializers.ListField(child=serializers.CharField(), required=False)
    best_time = serializers.CharField(required=False, allow_null=True)
    feature_importance = serializers.DictField(required=False)


class TrainingDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingData
        fields = [
            'id',
            'caption_length',
            'hashtag_count',
            'time_of_day',
            'day_of_week',
            'platform',
            'media_type',
            'brand_sentiment',
            'engagement_score',
            'data_type',
            'created_at',
        ]
        read_only_fields = ['created_at']


class ModelMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelMetrics
        fields = [
            'id',
            'version',
            'model_type',
            'training_samples',
            'r2_score',
            'mae',
            'rmse',
            'training_data_type',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['created_at']

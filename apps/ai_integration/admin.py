from django.contrib import admin
from .models import HashtagPerformance, OptimalPostingTime, EngagementForecast, TrainingData, ModelMetrics


@admin.register(HashtagPerformance)
class HashtagPerformanceAdmin(admin.ModelAdmin):
    list_display = ('hashtag', 'industry', 'platform', 'avg_engagement_rate', 'trending')
    list_filter = ('industry', 'platform', 'trending')
    search_fields = ('hashtag',)
    ordering = ('-avg_engagement_rate',)


@admin.register(OptimalPostingTime)
class OptimalPostingTimeAdmin(admin.ModelAdmin):
    list_display = ('platform', 'get_day_display', 'hour', 'engagement_score')
    list_filter = ('platform', 'day_of_week')
    ordering = ('platform', 'day_of_week', 'hour')
    
    def get_day_display(self, obj):
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return days[obj.day_of_week]
    get_day_display.short_description = 'Day'


@admin.register(EngagementForecast)
class EngagementForecastAdmin(admin.ModelAdmin):
    list_display = [
        'post',
        'engagement_level',
        'predicted_engagement_score',
        'actual_engagement_score',
        'predicted_at'
    ]
    list_filter = ['engagement_level', 'platform', 'media_type', 'predicted_at']
    search_fields = ['post__title', 'post__id']
    readonly_fields = [
        'caption_length',
        'hashtag_count',
        'time_of_day',
        'day_of_week',
        'predicted_engagement_score',
        'confidence_score',
        'predicted_at',
        'updated_at'
    ]


@admin.register(TrainingData)
class TrainingDataAdmin(admin.ModelAdmin):
    list_display = ['id', 'platform', 'media_type', 'engagement_score', 'data_type', 'created_at']
    list_filter = ['platform', 'media_type', 'data_type', 'created_at']
    readonly_fields = ['created_at']


@admin.register(ModelMetrics)
class ModelMetricsAdmin(admin.ModelAdmin):
    list_display = ['version', 'model_type', 'r2_score', 'mae', 'rmse', 'is_active', 'created_at']
    list_filter = ['model_type', 'is_active', 'created_at']
    readonly_fields = ['created_at']

from django.urls import path
from . import views

app_name = 'ai_integration'

urlpatterns = [
    # Hashtag Optimizer
    path('hashtags/suggest/', views.suggest_hashtags, name='suggest_hashtags'),
    
    # Mood & Tone Analysis
    path('caption/analyze-mood/', views.analyze_mood_and_tone, name='analyze_mood_and_tone'),
    
    # Caption Improvement
    path('caption/improve/', views.improve_caption, name='improve_caption'),
    
    # Generate Content by Mood
    path('caption/generate-by-mood/', views.generate_content_by_mood, name='generate_content_by_mood'),
    
    # Rewrite Caption by Mood/Tone
    path('caption/rewrite-by-mood/', views.rewrite_caption_by_mood, name='rewrite_caption_by_mood'),
    
    # Campaign Theme Detection
    path('campaign/detect-theme/', views.detect_campaign_theme, name='detect_campaign_theme'),
    
    # =========================================================================
    # Engagement Forecast API Endpoints
    # =========================================================================
    
    # Predict engagement for a post before publishing
    path('predict-engagement/', views.EngagementPredictionView.as_view(), name='predict_engagement'),
    
    # Get engagement forecast for a specific post
    path('engagement-forecast/<int:post_id>/', views.EngagementForecastDetailView.as_view(), name='engagement_forecast_detail'),
    
    # Get current model metrics and performance
    path('model-metrics/', views.ModelMetricsView.as_view(), name='model_metrics'),
    
    # Get optimal posting times for a platform
    path('optimal-posting-times/', views.get_optimal_posting_times, name='optimal_posting_times'),
]

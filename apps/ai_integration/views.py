from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from .models import EngagementForecast, ModelMetrics
from .serializers import (
    EngagementForecastSerializer,
    EngagementPredictionRequestSerializer,
    EngagementPredictionResponseSerializer,
    ModelMetricsSerializer,
)
from .services.ml_service import EngagementForecastModel
import logging

logger = logging.getLogger(__name__)


def get_gemini_service():
    """Lazy-load Gemini service to avoid import errors at Django startup"""
    from .services.gemini_service import GeminiService
    return GeminiService()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def suggest_hashtags(request):
    """
    Suggest best hashtags for a post using Gemini AI
    
    Request:
    {
        "caption": "Just finished my workout! 💪",  # Required
        "platform": "instagram",  # Optional, default: instagram
        "count": 10,  # Optional, default: 10
        "industry": "fitness"  # Optional - for hints
    }
    
    Response:
    {
        "hashtags": ["#fitness", "#gym", "#workout", ...],
        "industry": "fitness",
        "platform": "instagram",
        "reasoning": "These hashtags are trending...",
        "count": 10
    }
    """
    try:
        caption = request.data.get('caption')
        platform = request.data.get('platform', 'instagram')
        count = request.data.get('count', 10)
        industry = request.data.get('industry')
        
        if not caption:
            return Response(
                {'error': 'caption is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not caption.strip():
            return Response(
                {'error': 'caption cannot be empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate platform
        valid_platforms = ['instagram', 'facebook', 'linkedin']
        if platform not in valid_platforms:
            return Response(
                {'error': f'platform must be one of: {", ".join(valid_platforms)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate count
        if not isinstance(count, int) or count < 1 or count > 30:
            return Response(
                {'error': 'count must be between 1 and 30'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get Gemini service and analyze caption
        gemini = get_gemini_service()
        result = gemini.analyze_caption_for_hashtags(
            caption=caption,
            platform=platform,
            count=count,
            industry=industry
        )
        
        if 'error' in result and not result.get('hashtags'):
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in suggest_hashtags: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_mood_and_tone(request):
    """
    Extract mood and tone from a caption
    
    Request:
    {
        "caption": "Just finished my workout! 💪"
    }
    
    Response:
    {
        "mood": "positive",
        "tone": "enthusiastic",
        "confidence": 0.95,
        "description": "The caption expresses energetic excitement..."
    }
    """
    try:
        caption = request.data.get('caption')
        
        if not caption:
            return Response(
                {'error': 'caption is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        gemini = get_gemini_service()
        result = gemini.extract_mood_and_tone(caption)
        
        if 'error' in result:
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in analyze_mood_and_tone: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def improve_caption(request):
    """
    Get suggestions to improve a caption
    
    Request:
    {
        "caption": "Check out my new post",
        "platform": "instagram"  # Optional
    }
    
    Response:
    {
        "improved_caption": "Just dropped something special! 🔥...",
        "improvements": ["Add emoji for engagement", "Be more specific..."],
        "reasoning": "The improved version is more engaging..."
    }
    """
    try:
        caption = request.data.get('caption')
        platform = request.data.get('platform', 'instagram')
        
        if not caption:
            return Response(
                {'error': 'caption is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"Improving caption: '{caption[:50]}...' for platform: {platform}")
        
        gemini = get_gemini_service()
        result = gemini.generate_caption_improvement(caption, platform)
        
        logger.info(f"Improvement result: {result}")
        
        if 'error' in result:
            logger.error(f"Improvement error: {result['error']}")
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in improve_caption: {str(e)}", exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def detect_campaign_theme(request):
    """
    Analyze multiple captions to detect overall campaign theme
    
    Request:
    {
        "captions": [
            "Just finished my workout!",
            "New gym equipment arrived",
            "Training tips for beginners"
        ]
    }
    
    Response:
    {
        "main_theme": "Fitness & Motivation",
        "sub_themes": ["workout tips", "equipment reviews"],
        "target_audience": "fitness enthusiasts",
        "content_style": "encouraging and informative",
        "recommendations": ["Add more transformation stories", "Include success testimonials"]
    }
    """
    try:
        captions = request.data.get('captions', [])
        
        if not captions:
            return Response(
                {'error': 'captions list is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not isinstance(captions, list):
            return Response(
                {'error': 'captions must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(captions) == 0:
            return Response(
                {'error': 'captions list cannot be empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        gemini = get_gemini_service()
        result = gemini.detect_campaign_theme(captions)
        
        if 'error' in result:
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in detect_campaign_theme: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_content_by_mood(request):
    """
    Generate captions matching specific mood and tone
    
    Request:
    {
        "topic": "fitness journey",
        "mood": "inspirational",
        "tone": "motivating",
        "platform": "instagram",
        "count": 3
    }
    
    Response:
    {
        "captions": [
            {
                "text": "Ready to crush your goals? 🚀 Every workout brings you closer...",
                "mood": "inspirational",
                "tone": "motivating"
            },
            ...
        ],
        "mood": "inspirational",
        "tone": "motivating",
        "count": 3
    }
    """
    try:
        topic = request.data.get('topic')
        mood = request.data.get('mood')
        tone = request.data.get('tone')
        platform = request.data.get('platform', 'instagram')
        count = request.data.get('count', 3)
        
        if not all([topic, mood, tone]):
            return Response(
                {'error': 'topic, mood, and tone are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_platforms = ['instagram', 'facebook', 'linkedin']
        if platform not in valid_platforms:
            return Response(
                {'error': f'platform must be one of: {", ".join(valid_platforms)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not isinstance(count, int) or count < 1 or count > 10:
            return Response(
                {'error': 'count must be between 1 and 10'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        gemini = get_gemini_service()
        result = gemini.generate_content_by_mood(
            topic=topic,
            mood=mood,
            tone=tone,
            platform=platform,
            count=count
        )
        
        if 'error' in result and not result.get('captions'):
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in generate_content_by_mood: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rewrite_caption_by_mood(request):
    """
    Rewrite an existing caption to match specific mood and tone
    
    Request:
    {
        "caption": "Check out my new post",
        "mood": "inspirational",
        "tone": "motivating",
        "platform": "instagram"
    }
    
    Response:
    {
        "original": "Check out my new post",
        "rewritten": "Ready to transform your life? 🚀 Here's something special...",
        "mood": "inspirational",
        "tone": "motivating",
        "explanation": "Added emotional hook and call-to-action...",
        "platform": "instagram"
    }
    """
    try:
        caption = request.data.get('caption')
        mood = request.data.get('mood')
        tone = request.data.get('tone')
        platform = request.data.get('platform', 'instagram')
        
        if not all([caption, mood, tone]):
            return Response(
                {'error': 'caption, mood, and tone are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not caption.strip():
            return Response(
                {'error': 'caption cannot be empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_platforms = ['instagram', 'facebook', 'linkedin']
        if platform not in valid_platforms:
            return Response(
                {'error': f'platform must be one of: {", ".join(valid_platforms)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        gemini = get_gemini_service()
        result = gemini.rewrite_caption_by_mood(
            caption=caption,
            mood=mood,
            tone=tone,
            platform=platform
        )
        
        if 'error' in result and not result.get('rewritten'):
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in rewrite_caption_by_mood: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# Engagement Forecast API Views
# ============================================================================


class EngagementPredictionView(APIView):
    """
    Predict engagement for a post before publishing using Gemini AI.
    
    POST /api/ai/predict-engagement/
    {
        "caption_length": 150,
        "hashtag_count": 15,
        "time_of_day": 14,
        "day_of_week": 2,
        "platform": "instagram",
        "media_type": "image",
        "brand_sentiment": 0.8,
        "post_id": 123  # Optional, to save forecast to DB
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            serializer = EngagementPredictionRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # Use Gemini for prediction
            gemini = get_gemini_service()
            
            prediction_data = {
                'caption_length': serializer.validated_data['caption_length'],
                'hashtag_count': serializer.validated_data['hashtag_count'],
                'time_of_day': serializer.validated_data['time_of_day'],
                'day_of_week': serializer.validated_data['day_of_week'],
                'platform': serializer.validated_data['platform'],
                'media_type': serializer.validated_data['media_type'],
                'brand_sentiment': serializer.validated_data['brand_sentiment'],
            }
            
            # Include caption if provided
            if 'caption' in serializer.validated_data and serializer.validated_data['caption']:
                prediction_data['caption'] = serializer.validated_data['caption']
            
            prediction = gemini.predict_engagement(prediction_data)
            
            # Save forecast if post_id provided
            post_id = serializer.validated_data.get('post_id')
            if post_id:
                try:
                    from apps.content.models import Post
                    post = Post.objects.get(id=post_id)
                    
                    EngagementForecast.objects.update_or_create(
                        post=post,
                        defaults={
                            'caption_length': serializer.validated_data['caption_length'],
                            'hashtag_count': serializer.validated_data['hashtag_count'],
                            'time_of_day': serializer.validated_data['time_of_day'],
                            'day_of_week': serializer.validated_data['day_of_week'],
                            'platform': serializer.validated_data['platform'],
                            'media_type': serializer.validated_data['media_type'],
                            'brand_sentiment': serializer.validated_data['brand_sentiment'],
                            'predicted_engagement_score': prediction.get('predicted_engagement_score', prediction.get('score', 50)),
                            'engagement_level': prediction.get('engagement_level', prediction.get('level', 'MEDIUM')),
                            'confidence_score': prediction.get('confidence_score', prediction.get('confidence', 75)),
                        }
                    )
                except Post.DoesNotExist:
                    logger.warning(f"Post with id {post_id} not found")
                except Exception as e:
                    logger.error(f"Error saving forecast: {e}")
            
            response_serializer = EngagementPredictionResponseSerializer(prediction)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in engagement prediction: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EngagementForecastDetailView(APIView):
    """
    Get engagement forecast for a specific post.
    
    GET /api/ai/engagement-forecast/<post_id>/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, post_id):
        try:
            from apps.content.models import Post
            
            post = Post.objects.get(id=post_id)
            forecast = EngagementForecast.objects.get(post=post)
            
            serializer = EngagementForecastSerializer(forecast)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except EngagementForecast.DoesNotExist:
            return Response(
                {'error': 'No forecast found for this post'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error retrieving forecast: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ModelMetricsView(APIView):
    """
    Get current model metrics and performance.
    
    GET /api/ai/model-metrics/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Get active model
            active_model = ModelMetrics.objects.filter(is_active=True).first()
            
            if not active_model:
                return Response(
                    {'error': 'No active model found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = ModelMetricsSerializer(active_model)
            
            # Add feature importance if available
            try:
                model = EngagementForecastModel(model_type=active_model.model_type)
                feature_importance = model.get_feature_importance()
                response_data = serializer.data
                response_data['feature_importance'] = dict(list(feature_importance.items())[:5])
                return Response(response_data, status=status.HTTP_200_OK)
            except:
                return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error retrieving model metrics: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_optimal_posting_times(request):
    """
    Get optimal posting times for a specific platform.
    
    Request:
    {
        "platform": "instagram"
    }
    
    Response:
    {
        "platform": "instagram",
        "optimal_times": [
            {"day": "Tuesday", "hour": 11, "engagement_score": 85.5},
            {"day": "Tuesday", "hour": 19, "engagement_score": 82.3},
            ...
        ]
    }
    """
    try:
        from .models import OptimalPostingTime
        
        platform = request.data.get('platform', 'instagram')
        valid_platforms = ['instagram', 'facebook', 'linkedin']
        
        if platform not in valid_platforms:
            return Response(
                {'error': f'platform must be one of: {", ".join(valid_platforms)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        times = OptimalPostingTime.objects.filter(platform=platform).order_by('-engagement_score')[:10]
        
        day_names = {
            0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday',
            4: 'Friday', 5: 'Saturday', 6: 'Sunday'
        }
        
        optimal_times = [
            {
                'day': day_names[time.day_of_week],
                'hour': time.hour,
                'engagement_score': time.engagement_score,
            }
            for time in times
        ]
        
        return Response({
            'platform': platform,
            'optimal_times': optimal_times
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error retrieving optimal posting times: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
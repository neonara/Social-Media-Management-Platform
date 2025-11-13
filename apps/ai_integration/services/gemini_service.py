"""
Gemini API service for AI features
Handles caption analysis, hashtag generation, and mood extraction
"""

import json
import logging
import time
from django.conf import settings
from typing import Dict, List, Optional
from functools import wraps

logger = logging.getLogger(__name__)


def convert_24h_to_12h(time_24h: str) -> str:
    """
    Convert 24-hour format time to 12-hour format with AM/PM
    
    Args:
        time_24h: Time in 24-hour format (e.g., "14:00", "08:30")
    
    Returns:
        Time in 12-hour format (e.g., "2:00 PM", "8:30 AM")
    """
    try:
        hours, minutes = map(int, time_24h.split(':'))
        
        # Determine AM/PM
        period = 'AM' if hours < 12 else 'PM'
        
        # Convert to 12-hour format
        if hours == 0:
            hours_12 = 12
        elif hours > 12:
            hours_12 = hours - 12
        else:
            hours_12 = hours
        
        return f"{hours_12}:{minutes:02d} {period}"
    except (ValueError, IndexError):
        # If parsing fails, return the original
        return time_24h


def clean_json_response(text: str) -> str:
    """
    Clean JSON response from Gemini by removing markdown, etc.
    Does NOT remove escape sequences (\n, \t, \\, etc.) as they are valid JSON.
    
    Args:
        text: Raw text response from Gemini
        
    Returns:
        Cleaned JSON string
    """
    # Remove markdown code blocks
    if text.startswith('```'):
        if text.startswith('```json'):
            text = text[7:]
        else:
            text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    
    # IMPORTANT: Do not remove backslashes or other chars that are part of JSON escaping
    # Only remove actual null characters and control chars that appear outside of strings
    # For safety, we'll use a more conservative approach: only strip leading/trailing whitespace
    
    # Strip whitespace
    return text.strip()


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator to retry API calls with exponential backoff for rate limiting
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (multiplied by 2 each retry)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e)
                    last_exception = e
                    
                    # Check if it's a rate limit error
                    is_rate_limit = (
                        '429' in error_str or 
                        'RESOURCE_EXHAUSTED' in error_str or
                        'Too Many Requests' in error_str
                    )
                    
                    if is_rate_limit and attempt < max_retries - 1:
                        logger.warning(
                            f"Rate limited on attempt {attempt + 1}/{max_retries}. "
                            f"Waiting {delay}s before retry. Error: {error_str}"
                        )
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                    else:
                        raise
            
            raise last_exception
        return wrapper
    return decorator


class GeminiService:
    """Service for interacting with Google Gemini API"""

    def __init__(self):
        """Initialize Gemini API"""
        from google import genai
        
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY not configured in settings")
        
        # Create client with API key (auto-reads GEMINI_API_KEY env var if key is None)
        self.client = genai.Client(api_key=api_key)
        self.model = 'gemini-2.0-flash-001'

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def analyze_caption_for_hashtags(
        self,
        caption: str,
        platform: str = 'instagram',
        count: int = 10,
        industry: Optional[str] = None
    ) -> Dict:
        """
        Analyze caption using Gemini and suggest relevant hashtags
        
        Args:
            caption: User's caption text
            platform: Target platform (instagram, facebook, linkedin)
            count: Number of hashtags to suggest
            industry: Optional industry hint (fitness, fashion, tech, etc.)
        
        Returns:
            Dict with hashtags, industry detected, and reasoning
        """
        prompt = self._build_hashtag_prompt(caption, platform, count, industry)
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        
        # Parse the response
        result = self._parse_hashtag_response(response.text)
        return result

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def extract_mood_and_tone(self, caption: str) -> Dict:
        """
        Extract mood and tone from caption
        
        Args:
            caption: Caption text to analyze
        
        Returns:
            Dict with mood, tone, confidence, and description
        """
        prompt = f"""Analyze the mood and tone of this caption. Return a JSON response with:
- mood: (positive, negative, neutral, mixed)
- tone: (enthusiastic, professional, casual, sad, humorous, inspirational, etc.)
- confidence: (0-1) how confident you are
- description: brief explanation

Caption: {json.dumps(caption)}

Respond with ONLY valid JSON, no markdown or extra text."""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        
        # Parse JSON response
        text = clean_json_response(response.text)
        result = json.loads(text)
        return result

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def generate_caption_improvement(
        self,
        caption: str,
        platform: str = 'instagram'
    ) -> Dict:
        """
        Suggest improvements to a caption
        
        Args:
            caption: Original caption
            platform: Target platform
        
        Returns:
            Dict with improved caption and suggestions
        """
        prompt = f"""Improve this {platform} caption. Suggest a better version and explain why.
Original caption: {json.dumps(caption)}

Respond with JSON:
{{
    "improved_caption": "...",
    "improvements": ["improvement 1", "improvement 2"],
    "reasoning": "why these changes help"
}}

Use ONLY valid JSON, no markdown."""

        logger.info(f"Generating caption improvement prompt for: {caption[:50]}...")
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        
        logger.info(f"Gemini response received: {response.text[:100]}...")
        
        text = clean_json_response(response.text)
        result = json.loads(text)
        logger.info(f"Successfully parsed improvement result")
        return result

    def _build_hashtag_prompt(
        self,
        caption: str,
        platform: str,
        count: int,
        industry: Optional[str]
    ) -> str:
        """Build prompt for hashtag analysis"""
        
        industry_hint = f" (Industry: {industry})" if industry else ""
        
        prompt = f"""Analyze this social media caption and suggest the BEST {count} hashtags for {platform}{industry_hint}.

Caption: {json.dumps(caption)}

Requirements:
1. Hashtags must be relevant to the caption content
2. Prefer trending hashtags for {platform}
3. Mix popular and niche hashtags
4. Return ONLY valid JSON with NO extra text or markdown

Respond with this exact JSON format:
{{
    "hashtags": ["hashtag1", "hashtag2", ...],
    "industry": "detected_industry",
    "platform": "{platform}",
    "reasoning": "brief explanation of why these hashtags work"
}}"""
        
        return prompt

    def _parse_hashtag_response(self, response_text: str) -> Dict:
        """Parse Gemini's hashtag response"""
        try:
            # Clean up the response with helper function
            text = clean_json_response(response_text)
            
            # Parse JSON
            result = json.loads(text)
            
            # Ensure hashtags have # prefix
            hashtags = result.get('hashtags', [])
            if hashtags and not hashtags[0].startswith('#'):
                hashtags = [f'#{tag}' if not tag.startswith('#') else tag for tag in hashtags]
            
            return {
                'hashtags': hashtags,
                'industry': result.get('industry', 'general'),
                'platform': result.get('platform', 'instagram'),
                'reasoning': result.get('reasoning', ''),
                'count': len(hashtags)
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {response_text}")
            return {
                'error': f'Invalid JSON response: {str(e)}',
                'hashtags': [],
                'industry': 'general',
                'reasoning': 'Failed to parse response'
            }

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def detect_campaign_theme(self, captions: List[str]) -> Dict:
        """
        Analyze multiple captions to detect overall campaign theme
        
        Args:
            captions: List of caption texts
        
        Returns:
            Dict with detected themes and insights
        """
        captions_text = '\n'.join([f"- {cap}" for cap in captions[:5]])  # Max 5
        
        prompt = f"""Analyze these captions and identify the overall campaign theme/strategy.
Captions:
{captions_text}

Respond with JSON:
{{
    "main_theme": "...",
    "sub_themes": ["theme1", "theme2"],
    "target_audience": "...",
    "content_style": "...",
    "recommendations": ["rec1", "rec2"]
}}

ONLY JSON, no markdown."""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        
        text = clean_json_response(response.text)
        result = json.loads(text)
        return result

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def generate_content_by_mood(
        self,
        topic: str,
        mood: str,
        tone: str,
        platform: str = 'instagram',
        count: int = 3
    ) -> Dict:
        """
        Generate captions matching specific mood and tone
        
        Args:
            topic: What the content is about
            mood: Target mood (positive, inspirational, humorous, etc.)
            tone: Target tone (enthusiastic, professional, casual, etc.)
            platform: Target platform
            count: Number of variations to generate
        
        Returns:
            Dict with generated captions matching mood/tone
        """
        prompt = f"""Generate {count} unique {platform} captions about "{topic}".

Each caption MUST have these characteristics:
- Mood: {mood}
- Tone: {tone}
- Suitable for {platform} platform
- Engaging and authentic
- Different from each other

Respond with ONLY valid JSON:
{{
    "captions": [
        {{
            "text": "Caption text here...",
            "mood": "{mood}",
            "tone": "{tone}"
        }},
        ...
    ]
}}

No markdown, just JSON."""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        
        text = clean_json_response(response.text)
        result = json.loads(text)
        return {
            'captions': result.get('captions', []),
            'mood': mood,
            'tone': tone,
            'platform': platform,
            'count': len(result.get('captions', []))
        }

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def predict_engagement(self, post_data: Dict) -> Dict:
        """
        Predict engagement for a post using Gemini AI
        
        Args:
            post_data: Dict with keys:
                - caption (optional but recommended - actual post text)
                - caption_length
                - hashtag_count
                - time_of_day (string in "HH:MM" format, e.g. "21:30")
                - day_of_week (0-6, Mon-Sun)
                - platform (facebook, instagram, linkedin)
                - media_type (image, video, carousel, text)
                - brand_sentiment (-1.0 to 1.0)
        
        Returns:
            Dict with prediction data (score, level, confidence, best_time in 12-hour format)
        """
        try:
            platform = post_data.get('platform', 'instagram')
            media_type = post_data.get('media_type', 'image')
            caption = post_data.get('caption', '')
            caption_length = post_data.get('caption_length', len(caption) if caption else 100)
            hashtag_count = post_data.get('hashtag_count', 10)
            time_of_day = post_data.get('time_of_day', '12:00')  # In 24-hour format HH:MM
            day_of_week = post_data.get('day_of_week', 2)
            sentiment = post_data.get('brand_sentiment', 0.5)
            
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            # Convert 24-hour format to 12-hour format for the prompt
            time_12h = convert_24h_to_12h(time_of_day)
            
            # Build prompt with caption if provided
            caption_section = ""
            if caption and caption.strip():
                caption_section = f"""
Caption Content: {json.dumps(caption)}
"""
            
            # Build improvement suggestions section
            improvements_section = ""
            if caption and caption.strip():
                improvements_section = """

ALSO provide 3 specific, actionable improvements to increase engagement to HIGH level. Focus on:
1. Caption content and messaging
2. Hashtag strategy
3. Posting time or media type optimization"""

            prompt = f"""You are a social media marketing expert analyzing posting times.

KEY GUIDELINES FOR POSTING TIMES:
- {platform.capitalize()} users are typically most active during morning (6-9 AM), midday lunch (11 AM-2 PM), and evening (5-11 PM)
- People check social media when waking up, during breaks, after work, and before bed
- Weekday patterns differ from weekends
- Posting time affects visibility due to feed algorithms and user activity

POST DETAILS:
Platform: {platform.capitalize()}
Media Type: {media_type.capitalize()}
Current Posting Time: {time_12h} on {days[day_of_week]}
Caption Length: {caption_length} characters
Hashtags: {hashtag_count}
Brand Sentiment: {sentiment}{caption_section}{improvements_section}

TASK:
1. Predict engagement for posting at the CURRENT time: {time_12h}
2. If current time is in a PEAK period for {platform.capitalize()}, consider it a strength and boost the engagement score slightly, and return null for best_time
3. If current time is NOT in a peak period AND a significantly better time exists, suggest ONE specific time and return null for best_time
4. If current time is NOT peak but changing time won't make significant difference, return null for best_time anyway
5. Consider day of week - weekday patterns differ from weekends

Return ONLY valid JSON (no markdown):
{{
  "score": <0-100>,
  "level": "<HIGH|MEDIUM|LOW>",
  "confidence": <0-100>,
  "reasoning": "<brief explanation of engagement prediction>",
  "top_factors": ["<factor 1>", "<factor 2>", "<factor 3>"],
  "improvements": ["<improvement 1>", "<improvement 2>", "<improvement 3>"],
  "best_time": null or "<suggest ONE specific time like '9:00 AM' or '6:30 PM' only if significantly better>"
}}"""
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            # Parse response with cleaning
            text = clean_json_response(response.text)
            prediction_data = json.loads(text)
            
            # Get best_time - Gemini returns it in 12-hour format already
            best_time = prediction_data.get('best_time')
            
            # Map response to expected format
            return {
                'predicted_engagement_score': prediction_data.get('score', 50),
                'engagement_level': prediction_data.get('level', 'MEDIUM'),
                'confidence_score': prediction_data.get('confidence', 75),
                'reasoning': prediction_data.get('reasoning', 'Post analysis by Gemini'),
                'top_factors': prediction_data.get('top_factors', []),
                'improvements': prediction_data.get('improvements', []),
                'best_time': best_time,  # In 12-hour format like "8:00 PM"
                'model': 'gemini-2.0-flash',
                # Also keep the simpler keys for compatibility
                'score': prediction_data.get('score', 50),
                'level': prediction_data.get('level', 'MEDIUM'),
                'confidence': prediction_data.get('confidence', 75)
            }
            
        except Exception as e:
            logger.error(f"Error predicting engagement: {str(e)}")
            return {
                'predicted_engagement_score': 50,
                'engagement_level': 'MEDIUM',
                'confidence_score': 50,
                'reasoning': 'Unable to process prediction',
                'top_factors': [],
                'improvements': [],
                'best_time': None,
                'model': 'gemini-2.0-flash',
                'score': 50,
                'level': 'MEDIUM',
                'confidence': 50,
                'error': str(e)
            }

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def rewrite_caption_by_mood(
        self,
        caption: str,
        mood: str,
        tone: str,
        platform: str = 'instagram'
    ) -> Dict:
        """
        Rewrite an existing caption to match specific mood and tone
        
        Args:
            caption: The existing caption to rewrite
            mood: Target mood (positive, inspirational, humorous, professional, casual, etc.)
            tone: Target tone (enthusiastic, professional, casual, sarcastic, etc.)
            platform: Target platform
        
        Returns:
            Dict with rewritten caption matching mood/tone
        """
        prompt = f"""Rewrite this caption to match the specified mood and tone:

Original caption:
{caption}

Requirements:
- Mood: {mood}
- Tone: {tone}
- Platform: {platform}
- Keep the core message/meaning intact
- Make it engaging and authentic
- Maintain appropriate length for {platform}

Respond with ONLY valid JSON (no markdown, no code blocks):
{{
    "rewritten": "The rewritten caption here...",
    "mood": "{mood}",
    "tone": "{tone}",
    "explanation": "Brief explanation of what changed"
}}"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        
        text = clean_json_response(response.text)
        result = json.loads(text)
        return {
            'original': caption,
            'rewritten': result.get('rewritten', ''),
            'mood': mood,
            'tone': tone,
            'explanation': result.get('explanation', ''),
            'platform': platform
        }


# Singleton instance
_gemini_service = None


def get_gemini_service() -> GeminiService:
    """Get or create Gemini service instance"""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service

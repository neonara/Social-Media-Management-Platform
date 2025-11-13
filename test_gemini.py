"""
Quick test script to verify Gemini API integration works
Run with: python test_gemini.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'planit.settings')
sys.path.insert(0, '/home/achref/Desktop/planit/backend')
django.setup()

from apps.ai_integration.services.gemini_service import GeminiService

print("🧪 Testing Gemini Service Integration...\n")

# Test 1: Initialize service
print("1️⃣  Initializing Gemini Service...")
try:
    service = GeminiService()
    print("   ✅ Service initialized successfully\n")
except Exception as e:
    print(f"   ❌ Failed to initialize: {e}\n")
    sys.exit(1)

# Test 2: Hashtag suggestion
print("2️⃣  Testing hashtag suggestion...")
caption = "Just finished my morning workout! Feeling energized 💪"
try:
    result = service.analyze_caption_for_hashtags(
        caption=caption,
        platform='instagram',
        count=5
    )
    print(f"   Caption: {caption}")
    print(f"   ✅ Hashtags suggested: {result['hashtags']}")
    print(f"   Industry detected: {result['industry']}")
    print(f"   Reasoning: {result['reasoning'][:100]}...\n")
except Exception as e:
    print(f"   ❌ Failed: {e}\n")
    sys.exit(1)

# Test 3: Mood analysis
print("3️⃣  Testing mood analysis...")
try:
    mood_result = service.extract_mood_and_tone(caption)
    print(f"   Caption: {caption}")
    print(f"   ✅ Mood: {mood_result['mood']}")
    print(f"   Tone: {mood_result['tone']}")
    print(f"   Confidence: {mood_result['confidence']}\n")
except Exception as e:
    print(f"   ❌ Failed: {e}\n")
    sys.exit(1)

# Test 4: Caption improvement
print("4️⃣  Testing caption improvement...")
test_caption = "Check out my new post"
try:
    improve_result = service.generate_caption_improvement(
        caption=test_caption,
        platform='instagram'
    )
    print(f"   Original: {test_caption}")
    print(f"   ✅ Improved: {improve_result['improved_caption']}")
    print(f"   Suggestions: {improve_result['improvements']}\n")
except Exception as e:
    print(f"   ❌ Failed: {e}\n")
    sys.exit(1)

# Test 5: Campaign theme detection
print("5️⃣  Testing campaign theme detection...")
captions = [
    "Just finished my workout!",
    "New gym equipment arrived",
    "Training tips for beginners"
]
try:
    theme_result = service.detect_campaign_theme(captions)
    print(f"   ✅ Main theme: {theme_result['main_theme']}")
    print(f"   Target audience: {theme_result['target_audience']}")
    print(f"   Content style: {theme_result['content_style']}\n")
except Exception as e:
    print(f"   ❌ Failed: {e}\n")
    sys.exit(1)

print("🎉 All tests passed! Gemini service is working correctly.")

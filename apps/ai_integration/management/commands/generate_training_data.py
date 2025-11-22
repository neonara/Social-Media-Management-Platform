"""
Management command to generate synthetic engagement data for ML model training.
Creates 500+ training examples with realistic correlations between features and engagement.
"""

import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.ai_integration.models import TrainingData, ModelMetrics
import numpy as np


class Command(BaseCommand):
    help = "Generate synthetic engagement dataset for ML model training"

    def add_arguments(self, parser):
        parser.add_argument(
            "--samples",
            type=int,
            default=500,
            help="Number of synthetic samples to generate (default: 500)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing synthetic training data before generating new data",
        )

    def handle(self, *args, **options):
        samples = options["samples"]
        clear_existing = options["clear"]

        if clear_existing:
            deleted_count, _ = TrainingData.objects.filter(
                data_type="synthetic"
            ).delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Cleared {deleted_count} existing synthetic training samples"
                )
            )

        self.stdout.write(
            self.style.WARNING(
                f"\n🚀 Generating {samples} synthetic engagement records...\n"
            )
        )

        # Generate synthetic data with realistic correlations
        training_data = self._generate_synthetic_data(samples)

        # Bulk create for performance
        TrainingData.objects.bulk_create(training_data, batch_size=100)

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Successfully generated {samples} synthetic training samples!"
            )
        )

        # Display statistics
        self._display_statistics()

    def _generate_synthetic_data(self, num_samples):
        """
        Generate synthetic training data with realistic correlations.

        Features:
        - caption_length: 10-500 characters
        - hashtag_count: 0-30 hashtags
        - time_of_day: 0-23 hours
        - day_of_week: 0-6 (Monday-Sunday)
        - platform: facebook, instagram, linkedin
        - media_type: image, video, carousel, text
        - brand_sentiment: 0-1 sentiment score

        Engagement score (target): 0-100

        Realistic correlations:
        - More hashtags = higher engagement (up to ~20, then diminishing returns)
        - Video content performs better than images/text
        - Platform matters: Instagram highest, LinkedIn medium, Facebook varies
        - Optimal posting times have higher engagement
        - Longer captions on LinkedIn, shorter on Instagram
        - Positive sentiment = higher engagement
        """
        training_records = []

        platforms = ["facebook", "instagram", "linkedin"]
        media_types = ["image", "video", "carousel", "text"]

        # Optimal posting times (platform, day, hour)
        optimal_times = {
            "instagram": [
                (1, 11),
                (1, 19),
                (2, 11),
                (3, 9),
                (4, 17),
                (5, 10),
            ],  # Tue 11am, Tue 7pm, etc
            "facebook": [(2, 13), (3, 12), (4, 13), (5, 12), (6, 10)],
            "linkedin": [(2, 8), (2, 12), (3, 8), (4, 8), (4, 12)],
        }

        np.random.seed(42)  # For reproducibility

        for _ in range(num_samples):
            platform = random.choice(platforms)
            media_type = random.choice(media_types)

            # Generate features
            caption_length = random.randint(10, 500)
            hashtag_count = random.randint(0, 30)
            time_of_day = random.randint(0, 23)
            day_of_week = random.randint(0, 6)
            brand_sentiment = random.uniform(0, 1)

            # Base engagement score
            engagement_score = 25.0

            # Platform impact
            platform_multiplier = {
                "instagram": 1.2,
                "facebook": 0.9,
                "linkedin": 1.0,
            }
            engagement_score *= platform_multiplier.get(platform, 1.0)

            # Media type impact
            media_impact = {
                "video": 1.4,
                "carousel": 1.25,
                "image": 1.1,
                "text": 0.8,
            }
            engagement_score *= media_impact.get(media_type, 1.0)

            # Hashtag impact (optimal around 15-20)
            hashtag_engagement = 1.0
            if hashtag_count > 0:
                if hashtag_count <= 20:
                    hashtag_engagement = 1.0 + (hashtag_count / 25)
                else:
                    hashtag_engagement = 1.8 - ((hashtag_count - 20) / 50)
            engagement_score *= hashtag_engagement

            # Caption length impact (platform dependent)
            if platform == "linkedin":
                # Longer captions better for LinkedIn
                caption_factor = 1.0 + min((caption_length / 500), 1.0)
            elif platform == "instagram":
                # Shorter or moderate captions better for Instagram
                caption_factor = 1.0 + (1 - abs(caption_length - 150) / 500)
            else:  # facebook
                caption_factor = 1.0 + (caption_length / 1000)

            engagement_score *= caption_factor

            # Optimal posting time impact
            is_optimal_time = (day_of_week, time_of_day) in optimal_times.get(
                platform, []
            )
            if is_optimal_time:
                engagement_score *= 1.3
            elif time_of_day in range(9, 17):  # Business hours
                engagement_score *= 1.1

            # Sentiment impact
            engagement_score *= 0.6 + (brand_sentiment * 0.8)

            # Add some random noise for realism
            noise = np.random.normal(0, 5)
            engagement_score += noise

            # Clamp to 0-100
            engagement_score = max(0, min(100, engagement_score))

            training_record = TrainingData(
                caption_length=caption_length,
                hashtag_count=hashtag_count,
                time_of_day=time_of_day,
                day_of_week=day_of_week,
                platform=platform,
                media_type=media_type,
                brand_sentiment=brand_sentiment,
                engagement_score=engagement_score,
                data_type="synthetic",
            )
            training_records.append(training_record)

        return training_records

    def _display_statistics(self):
        """Display statistics about the generated training data"""
        self.stdout.write(self.style.SUCCESS("\n📊 Training Data Statistics:\n"))

        total_samples = TrainingData.objects.filter(data_type="synthetic").count()
        self.stdout.write(f"   Total samples: {total_samples}")

        # By platform
        platforms = (
            TrainingData.objects.filter(data_type="synthetic")
            .values("platform")
            .distinct()
        )
        for p in platforms:
            platform = p["platform"]
            count = TrainingData.objects.filter(
                data_type="synthetic", platform=platform
            ).count()
            avg_engagement = TrainingData.objects.filter(
                data_type="synthetic", platform=platform
            ).values_list("engagement_score", flat=True)
            if avg_engagement:
                avg = sum(avg_engagement) / len(avg_engagement)
                self.stdout.write(
                    f"   • {platform.title()}: {count} samples (avg engagement: {avg:.1f}/100)"
                )

        # By media type
        self.stdout.write("\n   By Media Type:")
        media_types = (
            TrainingData.objects.filter(data_type="synthetic")
            .values("media_type")
            .distinct()
        )
        for m in media_types:
            media_type = m["media_type"]
            count = TrainingData.objects.filter(
                data_type="synthetic", media_type=media_type
            ).count()
            avg_engagement = TrainingData.objects.filter(
                data_type="synthetic", media_type=media_type
            ).values_list("engagement_score", flat=True)
            if avg_engagement:
                avg = sum(avg_engagement) / len(avg_engagement)
                self.stdout.write(
                    f"   • {media_type.title()}: {count} samples (avg engagement: {avg:.1f}/100)"
                )

        # Overall stats
        all_scores = TrainingData.objects.filter(data_type="synthetic").values_list(
            "engagement_score", flat=True
        )
        if all_scores:
            scores_list = list(all_scores)
            self.stdout.write(f"\n   Overall Engagement Scores:")
            self.stdout.write(f"   • Min: {min(scores_list):.1f}")
            self.stdout.write(f"   • Max: {max(scores_list):.1f}")
            self.stdout.write(f"   • Avg: {sum(scores_list) / len(scores_list):.1f}")

        self.stdout.write(self.style.SUCCESS("\n✓ Data generation complete!\n"))

"""
Management command to generate mock analytics data for testing reports
"""
import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.content.models import Post
from apps.content.analytics_models import PostAnalytics
from apps.social_media.models import SocialPage
from apps.accounts.models import User


class Command(BaseCommand):
    help = "Generate mock analytics data for testing reports"

    def add_arguments(self, parser):
        parser.add_argument(
            "--posts",
            type=int,
            default=20,
            help="Number of posts to create per page (default: 20)",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Number of days in the past to generate data (default: 90)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing posts and analytics before generating",
        )

    def handle(self, *args, **options):
        posts_per_page = options["posts"]
        days_back = options["days"]
        clear_existing = options["clear"]

        if clear_existing:
            self.stdout.write("Clearing existing posts and analytics...")
            PostAnalytics.objects.all().delete()
            Post.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("✓ Cleared existing data"))

        # Get all social pages
        pages = SocialPage.objects.all()

        if not pages.exists():
            self.stdout.write(
                self.style.ERROR(
                    "No social pages found! Please create social pages first."
                )
            )
            return

        self.stdout.write(f"Found {pages.count()} social pages")

        total_posts = 0
        total_analytics = 0

        for page in pages:
            self.stdout.write(
                f"\nGenerating data for: {page.page_name} ({page.platform})"
            )

            # Generate posts for this page
            for i in range(posts_per_page):
                # Random date within the specified range
                days_ago = random.randint(0, days_back)
                post_date = timezone.now() - timedelta(days=days_ago)

                # Determine post status (80% published, 15% scheduled, 5% draft)
                status_roll = random.random()
                if status_roll < 0.80:
                    status = "published"
                    published_at = post_date
                elif status_roll < 0.95:
                    status = "scheduled"
                    published_at = timezone.now() + timedelta(days=random.randint(1, 7))
                else:
                    status = "draft"
                    published_at = None

                # Generate post content
                post_types = ["promotional", "educational", "engaging", "announcement"]
                post_type = random.choice(post_types)

                caption_templates = [
                    f"🎉 Exciting news from {page.page_name}! Check out our latest update. #{post_type} #socialmedia",
                    f"📢 New announcement! Stay tuned for more. #updates #news",
                    f"💡 Did you know? Here's a quick tip for you! #tips #{post_type}",
                    f"🌟 Another great moment to share with you all! #community",
                    f"🔥 Trending now! Don't miss out on this. #{post_type}",
                ]

                post = Post.objects.create(
                    platform_page=page,
                    client=page.client,
                    title=f"{post_type.capitalize()} Post #{i+1}",
                    description=random.choice(caption_templates),
                    status=status,
                    scheduled_for=published_at if status == "scheduled" else None,
                    published_at=published_at if status == "published" else None,
                    created_at=post_date,
                    platforms=[page.platform],  # JSON field with platform list
                )
                total_posts += 1

                # Only create analytics for published posts
                if status == "published":
                    # Generate realistic analytics based on platform
                    base_engagement = self._get_base_engagement(page.platform)

                    # Add some randomness (±40%)
                    reach = int(base_engagement["reach"] * random.uniform(0.6, 1.4))
                    impressions = int(
                        reach * random.uniform(1.2, 2.5)
                    )  # Impressions > reach
                    likes = int(base_engagement["likes"] * random.uniform(0.6, 1.4))
                    comments = int(
                        base_engagement["comments"] * random.uniform(0.6, 1.4)
                    )
                    shares = int(base_engagement["shares"] * random.uniform(0.6, 1.4))
                    clicks = int(base_engagement["clicks"] * random.uniform(0.6, 1.4))

                    # Calculate engagement rate (will be recalculated by model's save method)
                    total_engagements = likes + comments + shares
                    engagement_rate = (
                        (total_engagements / reach * 100) if reach > 0 else 0
                    )

                    # Create analytics
                    PostAnalytics.objects.create(
                        post=post,
                        likes=likes,
                        comments=comments,
                        shares=shares,
                        reach=reach,
                        impressions=impressions,
                        clicks=clicks,
                        engagement_rate=round(engagement_rate, 2),
                    )
                    total_analytics += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ Created {posts_per_page} posts for {page.page_name}"
                )
            )

        self.stdout.write(self.style.SUCCESS(f"\n✅ Successfully generated:"))
        self.stdout.write(self.style.SUCCESS(f"   • {total_posts} posts"))
        self.stdout.write(
            self.style.SUCCESS(f"   • {total_analytics} analytics records")
        )

    def _get_base_engagement(self, platform):
        """Get base engagement metrics based on platform"""
        engagement_by_platform = {
            "facebook": {
                "reach": 5000,
                "likes": 250,
                "comments": 30,
                "shares": 15,
                "clicks": 50,
            },
            "instagram": {
                "reach": 8000,
                "likes": 400,
                "comments": 50,
                "shares": 25,
                "clicks": 80,
            },
            "twitter": {
                "reach": 3000,
                "likes": 150,
                "comments": 20,
                "shares": 40,
                "clicks": 30,
            },
            "linkedin": {
                "reach": 2000,
                "likes": 80,
                "comments": 10,
                "shares": 15,
                "clicks": 60,
            },
            "tiktok": {
                "reach": 15000,
                "likes": 750,
                "comments": 100,
                "shares": 50,
                "clicks": 20,
            },
        }

        return engagement_by_platform.get(
            platform.lower(), engagement_by_platform["facebook"]  # Default to Facebook
        )

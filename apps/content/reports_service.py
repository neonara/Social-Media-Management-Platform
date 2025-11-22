"""
Service module for generating social media reports.
Handles all business logic for report generation, calculations, and data aggregation.
"""

from django.db.models import Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Tuple

from .models import Post
from apps.social_media.models import SocialPage
from apps.accounts.models import User


class ReportGenerationService:
    """Service class for generating social media performance reports."""

    @staticmethod
    def validate_report_parameters(
        client_id: int, page_id: int, report_type: str, period: str
    ) -> Tuple[User, SocialPage, datetime, datetime]:
        """
        Validate report parameters and return validated objects.

        Args:
            client_id: ID of the client
            page_id: ID of the social media page
            report_type: 'week' or 'month'
            period: Date string in format 'YYYY-MM-DD' for week or 'YYYY-MM' for month

        Returns:
            Tuple of (client, page, start_datetime, end_datetime)

        Raises:
            ValueError: If parameters are invalid
            User.DoesNotExist: If client not found
            SocialPage.DoesNotExist: If page not found
        """
        # Verify client exists and is a client
        try:
            client = User.objects.get(id=client_id, is_client=True)
        except User.DoesNotExist:
            raise ValueError(f"Client with ID {client_id} not found")

        # Verify page exists and belongs to client
        try:
            page = SocialPage.objects.get(id=page_id, client=client)
        except SocialPage.DoesNotExist:
            raise ValueError(
                f"Social media page with ID {page_id} not found for this client"
            )

        # Calculate date range
        try:
            if report_type == "week":
                # Period format: YYYY-MM-DD (start of week)
                start_date = datetime.strptime(period, "%Y-%m-%d").date()
                end_date = start_date + timedelta(days=6)
            elif report_type == "month":
                # Period format: YYYY-MM
                start_date = datetime.strptime(period + "-01", "%Y-%m-%d").date()
                # Get last day of month
                next_month = start_date + relativedelta(months=1)
                end_date = next_month - timedelta(days=1)
            else:
                raise ValueError(
                    f"Invalid report_type: {report_type}. Must be 'week' or 'month'"
                )
        except ValueError as e:
            raise ValueError(f"Invalid period format: {str(e)}")

        # Convert to datetime for query
        start_datetime = timezone.make_aware(
            datetime.combine(start_date, datetime.min.time())
        )
        end_datetime = timezone.make_aware(
            datetime.combine(end_date, datetime.max.time())
        )

        return client, page, start_datetime, end_datetime

    @staticmethod
    def get_published_posts(
        client: User, page: SocialPage, start_datetime: datetime, end_datetime: datetime
    ):
        """
        Retrieve published posts for the given parameters.

        Returns:
            QuerySet of Post objects
        """
        return (
            Post.objects.filter(
                client=client,
                platform_page=page,
                status="published",
                published_at__gte=start_datetime,
                published_at__lte=end_datetime,
            )
            .select_related("analytics")
            .prefetch_related("media")
        )

    @staticmethod
    def calculate_aggregate_metrics(posts) -> Dict:
        """
        Calculate aggregate metrics from posts.

        Returns:
            Dictionary with total_posts, total_engagement, total_reach, avg_engagement_rate
        """
        total_posts = posts.count()

        # Get analytics for posts that have them
        posts_with_analytics = posts.filter(analytics__isnull=False)

        if not posts_with_analytics.exists():
            return {
                "total_posts": total_posts,
                "total_engagement": 0,
                "total_reach": 0,
                "avg_engagement_rate": 0.0,
            }

        # Calculate totals
        analytics_data = posts_with_analytics.aggregate(
            total_likes=Sum("analytics__likes"),
            total_comments=Sum("analytics__comments"),
            total_shares=Sum("analytics__shares"),
            total_reach=Sum("analytics__reach"),
            avg_engagement_rate=Avg("analytics__engagement_rate"),
        )

        total_engagement = (
            (analytics_data["total_likes"] or 0)
            + (analytics_data["total_comments"] or 0)
            + (analytics_data["total_shares"] or 0)
        )

        return {
            "total_posts": total_posts,
            "total_engagement": total_engagement,
            "total_reach": analytics_data["total_reach"] or 0,
            "avg_engagement_rate": round(analytics_data["avg_engagement_rate"] or 0, 1),
        }

    @staticmethod
    def get_platform_breakdown(
        page: SocialPage, total_posts: int, total_engagement: int
    ) -> List[Dict]:
        """Generate platform breakdown data."""
        return [
            {
                "platform": page.platform.capitalize(),
                "posts": total_posts,
                "engagement": total_engagement,
            }
        ]

    @staticmethod
    def get_top_posts(posts, limit: int = 3) -> List[Dict]:
        """
        Get top performing posts sorted by engagement.

        Args:
            posts: QuerySet of posts
            limit: Number of top posts to return

        Returns:
            List of post dictionaries
        """
        top_posts = []
        posts_with_analytics = posts.filter(analytics__isnull=False)

        # Sort by total engagement (likes + comments + shares)
        sorted_posts = sorted(
            posts_with_analytics,
            key=lambda p: (
                p.analytics.likes + p.analytics.comments + p.analytics.shares
                if hasattr(p, "analytics")
                else 0
            ),
            reverse=True,
        )[:limit]

        for post in sorted_posts:
            top_posts.append(
                {
                    "id": post.id,
                    "content": (post.description[:100] + "...")
                    if len(post.description) > 100
                    else post.description,
                    "platform": post.platform_page.platform.capitalize()
                    if post.platform_page
                    else "Unknown",
                    "likes": post.analytics.likes if hasattr(post, "analytics") else 0,
                    "comments": post.analytics.comments
                    if hasattr(post, "analytics")
                    else 0,
                    "shares": post.analytics.shares
                    if hasattr(post, "analytics")
                    else 0,
                    "date": post.published_at.strftime("%Y-%m-%d")
                    if post.published_at
                    else "",
                }
            )

        return top_posts

    @staticmethod
    def calculate_engagement_trend(
        posts, report_type: str, start_date, end_date
    ) -> List[Dict]:
        """
        Calculate engagement trend data.

        Args:
            posts: QuerySet of posts
            report_type: 'week' or 'month'
            start_date: Start date
            end_date: End date

        Returns:
            List of engagement trend data points
        """
        engagement_trend = []
        posts_with_analytics = posts.filter(analytics__isnull=False)

        if report_type == "week":
            # Daily breakdown
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

            for i, day in enumerate(days):
                day_date = start_date.date() + timedelta(days=i)
                day_start = timezone.make_aware(
                    datetime.combine(day_date, datetime.min.time())
                )
                day_end = timezone.make_aware(
                    datetime.combine(day_date, datetime.max.time())
                )

                day_posts = posts_with_analytics.filter(
                    published_at__gte=day_start, published_at__lte=day_end
                )

                day_data = day_posts.aggregate(
                    total_likes=Sum("analytics__likes"),
                    total_comments=Sum("analytics__comments"),
                    total_shares=Sum("analytics__shares"),
                )

                day_engagement = (
                    (day_data["total_likes"] or 0)
                    + (day_data["total_comments"] or 0)
                    + (day_data["total_shares"] or 0)
                )

                engagement_trend.append({"date": day, "engagement": day_engagement})

        else:  # month
            # Weekly breakdown
            for week_num in range(4):
                week_start_date = start_date.date() + timedelta(days=week_num * 7)
                week_end_date = min(
                    week_start_date + timedelta(days=6), end_date.date()
                )

                week_start = timezone.make_aware(
                    datetime.combine(week_start_date, datetime.min.time())
                )
                week_end = timezone.make_aware(
                    datetime.combine(week_end_date, datetime.max.time())
                )

                week_posts = posts_with_analytics.filter(
                    published_at__gte=week_start, published_at__lte=week_end
                )

                week_data = week_posts.aggregate(
                    total_likes=Sum("analytics__likes"),
                    total_comments=Sum("analytics__comments"),
                    total_shares=Sum("analytics__shares"),
                )

                week_engagement = (
                    (week_data["total_likes"] or 0)
                    + (week_data["total_comments"] or 0)
                    + (week_data["total_shares"] or 0)
                )

                engagement_trend.append(
                    {"date": f"Week {week_num + 1}", "engagement": week_engagement}
                )

        return engagement_trend

    @classmethod
    def generate_report(
        cls, client_id: int, page_id: int, report_type: str, period: str
    ) -> Dict:
        """
        Main method to generate a complete report.

        Args:
            client_id: ID of the client
            page_id: ID of the social media page
            report_type: 'week' or 'month'
            period: Date string

        Returns:
            Dictionary containing complete report data

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate parameters
        client, page, start_datetime, end_datetime = cls.validate_report_parameters(
            client_id, page_id, report_type, period
        )

        # Get published posts
        posts = cls.get_published_posts(client, page, start_datetime, end_datetime)

        # If no posts found, return empty report
        if not posts.exists():
            return {
                "message": "No published posts found for this period",
                "totalPosts": 0,
                "totalEngagement": 0,
                "totalReach": 0,
                "totalFollowers": page.permissions.get("followers", 0)
                if isinstance(page.permissions, dict)
                else 0,
                "avgEngagementRate": 0,
                "platformBreakdown": [],
                "topPosts": [],
                "engagementTrend": [],
            }

        # Calculate aggregate metrics
        metrics = cls.calculate_aggregate_metrics(posts)

        # Get platform breakdown
        platform_breakdown = cls.get_platform_breakdown(
            page, metrics["total_posts"], metrics["total_engagement"]
        )

        # Get top posts
        top_posts = cls.get_top_posts(posts)

        # Calculate engagement trend
        engagement_trend = cls.calculate_engagement_trend(
            posts, report_type, start_datetime, end_datetime
        )

        # Build and return complete report
        return {
            "totalPosts": metrics["total_posts"],
            "totalEngagement": metrics["total_engagement"],
            "totalReach": metrics["total_reach"],
            "totalFollowers": page.permissions.get("followers", 0)
            if isinstance(page.permissions, dict)
            else 0,
            "avgEngagementRate": metrics["avg_engagement_rate"],
            "platformBreakdown": platform_breakdown,
            "topPosts": top_posts,
            "engagementTrend": engagement_trend,
        }

from celery import shared_task
import logging
from django.utils import timezone

from apps.content.models import Post
from .services import publish_to_facebook, publish_to_instagram, publish_to_linkedin
from .models import SocialPage

# Set up logger
logger = logging.getLogger(__name__)


@shared_task
def publish_scheduled_post(post_id):
    """Publish a specific post identified by post_id"""
    try:
        post = Post.objects.get(id=post_id)
        page = post.platform_page
        if not page or not page.is_token_valid():
            logger.error(f"Failed to publish post {post_id}: No valid access token")
            post.status = "failed"
            post.save()
            raise Exception(f"No valid access token for post {post_id}")

        if page.platform == "facebook":
            publish_to_facebook(post, page)
        elif page.platform == "instagram":
            publish_to_instagram(post, page)
        elif page.platform == "linkedin":
            publish_to_linkedin(post, page)

        post.status = "published"
        post.save()
        logger.info(f"Successfully published post {post_id} to {page.platform}")
    except Post.DoesNotExist:
        logger.error(f"Post with ID {post_id} not found")
    except Exception as e:
        logger.error(f"Error publishing post {post_id}: {str(e)}")
        # Only update status if post exists and was retrieved
        if "post" in locals():
            post.status = "failed"
            post.save()


@shared_task
def check_and_publish_scheduled_posts():
    """
    Periodic task that checks for posts scheduled for now or in the past
    and triggers their publication
    """
    try:
        now = timezone.now()
        # Find all scheduled posts that are due
        scheduled_posts = Post.objects.filter(
            status="scheduled",
            scheduled_for__lte=now,  # Posts scheduled for now or in the past
        )

        logger.info(f"Found {scheduled_posts.count()} scheduled posts to publish")

        for post in scheduled_posts:
            # Update status to prevent duplicate publishing
            post.status = "pending"
            post.save()

            # Check if post has a platform page
            if not post.platform_page:
                # Try to find a LinkedIn page for this user
                if "linkedin" in post.platforms:
                    try:
                        linkedin_page = SocialPage.objects.filter(
                            client=post.client, platform="linkedin"
                        ).first()

                        if linkedin_page and linkedin_page.is_token_valid():
                            post.platform_page = linkedin_page
                            post.save()
                        else:
                            logger.error(
                                f"No valid LinkedIn page found for post {post.id}"
                            )
                            post.status = "failed"
                            post.save()
                            continue
                    except Exception as e:
                        logger.error(f"Error finding LinkedIn page: {str(e)}")
                        post.status = "failed"
                        post.save()
                        continue

            # Queue the actual publishing task
            publish_scheduled_post.delay(post.id)

        return f"Processed {scheduled_posts.count()} scheduled posts"
    except Exception as e:
        logger.error(f"Error in check_and_publish_scheduled_posts: {str(e)}")
        return f"Error: {str(e)}"

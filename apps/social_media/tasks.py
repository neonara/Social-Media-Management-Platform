from celery import shared_task

from apps.content.models import Post
from services import publish_to_facebook, publish_to_instagram, publish_to_linkedin

@shared_task
def publish_scheduled_post(post_id):
    post = Post.objects.get(id=post_id)
    page = post.platform_page
    if not page or not page.is_token_valid():
        raise Exception("No valid access token")
    
    if page.platform == 'facebook':
        publish_to_facebook(post, page)
    elif page.platform == 'instagram':
        publish_to_instagram(post, page)
    elif page.platform == 'linkedin':
        publish_to_linkedin(post, page)
    
    post.status = 'published'
    post.save()

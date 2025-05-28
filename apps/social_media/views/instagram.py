import requests
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import redirect

from apps.social_media.models import SocialPage
from apps.social_media.serializers import SocialPageSerializer
from apps.social_media.services import publish_to_instagram
from apps.content.models import Post
from django.conf import settings
from rest_framework import status

GRAPH_API_VERSION = settings.FACEBOOK_GRAPH_API_VERSION
FB_APP_ID = settings.FACEBOOK_APP_ID
FB_APP_SECRET = settings.FACEBOOK_APP_SECRET
IG_REDIRECT_URI = settings.INSTAGRAM_REDIRECT_URI
IG_SCOPES = settings.INSTAGRAM_SCOPES

# Instagram Connection Views
class InstagramConnectView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        url = (
            f"https://www.facebook.com/{GRAPH_API_VERSION}/dialog/oauth?"
            f"client_id={FB_APP_ID}&redirect_uri={IG_REDIRECT_URI}&"
            f"scope={IG_SCOPES}&response_type=code"
        )
        return redirect(url)


class InstagramCallbackView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        code = request.GET.get("code")
        if not code:
            return Response({"error": "Missing code"}, status=400)

        # Step 1: Exchange code for access token
        token_url = (
            f"https://graph.facebook.com/{GRAPH_API_VERSION}/oauth/access_token?"
            f"client_id={FB_APP_ID}&redirect_uri={IG_REDIRECT_URI}"
            f"&client_secret={FB_APP_SECRET}&code={code}"
        )
        token_res = requests.get(token_url).json()
        access_token = token_res.get("access_token")

        if not access_token:
            return Response({"error": "Failed to retrieve access token"}, status=400)

        # Step 2: Get User's Pages
        pages_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/accounts?access_token={access_token}"
        pages_res = requests.get(pages_url).json()
        pages = pages_res.get("data", [])

        for page in pages:
            # Step 3: Get linked Instagram Business account
            ig_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page['id']}?fields=instagram_business_account&access_token={page['access_token']}"
            ig_res = requests.get(ig_url).json()
            ig_account = ig_res.get("instagram_business_account")

            if ig_account:
                SocialPage.objects.update_or_create(
                    user=request.user,
                    page_id=ig_account["id"],
                    platform="instagram",
                    defaults={
                        "page_name": f"Instagram via {page['name']}",
                        "access_token": page["access_token"],
                        "permissions": {"linked_facebook_page": page["id"]}
                    }
                )
                return Response({"success": True, "instagram_account_id": ig_account["id"]})

        return Response({"error": "No Instagram Business Account linked to your Facebook pages."}, status=404)


class InstagramDisconnectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        deleted, _ = SocialPage.objects.filter(client=request.user, platform="instagram").delete()
        return Response({"disconnected": deleted > 0})

class InstagramPageView(APIView):
    """
    Get Instagram page details for current user
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            page = SocialPage.objects.get(client=request.user, platform='instagram')
            serializer = SocialPageSerializer(page)
            return Response(serializer.data)
        except SocialPage.DoesNotExist:
            # Return a 200 response with connected=False instead of 404
            return Response({
                'connected': False,
                'platform': 'instagram',
                'message': 'No Instagram page connected'
            }, status=200)

class PublishToInstagramView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id, *args, **kwargs):
        try:
            post = Post.objects.get(id=post_id)

            if post.client != request.user and not request.user.is_staff:
                return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

            page = post.platform_page or SocialPage.objects.filter(client=post.client, platform='instagram').first()

            if not page or not page.is_token_valid():
                return Response({"error": "Invalid or missing Instagram page token."}, status=400)

            ig_post_id = publish_to_instagram(post, page)

            post.instagram_post_id = ig_post_id
            post.status = "published"
            post.save()

            return Response({"success": True, "instagram_post_id": ig_post_id}, status=200)

        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

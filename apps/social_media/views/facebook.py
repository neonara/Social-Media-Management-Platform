import requests
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import redirect

from apps.social_media.models import SocialPage
from apps.social_media.serializers import SocialPageSerializer
from apps.social_media.services import (
    exchange_code_for_access_token, 
    extend_to_long_lived_token, 
    fetch_user_pages,
    publish_to_facebook
)
from apps.content.models import Post
from django.conf import settings
from rest_framework import status

GRAPH_API_VERSION = settings.FACEBOOK_GRAPH_API_VERSION
FB_APP_ID = settings.FACEBOOK_APP_ID
FB_APP_SECRET = settings.FACEBOOK_APP_SECRET
FB_REDIRECT_URI = settings.FACEBOOK_REDIRECT_URI
FB_SCOPES = settings.FACEBOOK_SCOPES

# Facebook Connection Views
class FacebookConnectView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        url = (  
            f"https://www.facebook.com/{GRAPH_API_VERSION}/dialog/oauth?"
            f"client_id={FB_APP_ID}&redirect_uri={FB_REDIRECT_URI}"
            f"&scope={FB_SCOPES}&response_type=code"
        )
        return redirect(url)


class FacebookCallbackView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        code = request.query_params.get("code")
        if not code:
            return Response({"error": "Missing authorization code"}, status=400)

        try:
            # Step 1: Exchange and extend token
            short_token = exchange_code_for_access_token(code)
            long_token = extend_to_long_lived_token(short_token)

            # Step 2: Get user first and last name from Graph API
            user_info_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me"
            params = {
                "fields": "first_name,last_name",
                "access_token": long_token
            }
            user_info = requests.get(user_info_url, params=params).json()

            # Step 3: Update user's first and last name
            user = request.user
            user.first_name = user_info.get("first_name", user.first_name)
            user.last_name = user_info.get("last_name", user.last_name)
            user.save()

            # Step 4: Fetch Facebook pages
            pages = fetch_user_pages(long_token)
            if not pages:
                return Response({"error": "No Facebook Pages found."}, status=400)

            page = pages[0]

            SocialPage.objects.update_or_create(
                user=request.user,
                page_id=page["id"],
                platform="facebook",
                defaults={
                    "page_name": page["name"],
                    "access_token": page["access_token"],
                    "permissions": {"tasks": page.get("tasks", [])}
                }
            )

            return Response({"success": True, "page": page}, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class FacebookDisconnectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        deleted, _ = SocialPage.objects.filter(client=request.user, platform="facebook").delete()
        return Response({"disconnected": deleted > 0})

class FacebookPageView(APIView):
    """
    Get Facebook page details for current user
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            page = SocialPage.objects.get(client=request.user, platform='facebook')
            serializer = SocialPageSerializer(page)
            return Response(serializer.data)
        except SocialPage.DoesNotExist:
            # Return a 200 response with connected=False instead of 404
            return Response({
                'connected': False,
                'platform': 'facebook',
                'message': 'No Facebook page connected'
            }, status=200)



class PublishToFacebookView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id, *args, **kwargs):
        try:
            post = Post.objects.get(id=post_id)

            if post.client != request.user and not request.user.is_staff:
                return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

            page = post.platform_page or SocialPage.objects.filter(user=post.client, platform='facebook').first()

            if not page or not page.is_token_valid():
                return Response({"error": "Invalid or missing Facebook page token."}, status=400)

            fb_post_id = publish_to_facebook(post, page)

            post.facebook_post_id = fb_post_id
            post.status = "published"
            post.save()

            return Response({"success": True, "facebook_post_id": fb_post_id}, status=200)

        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
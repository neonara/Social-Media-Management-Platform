from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from apps.content.models import Post
from services import publish_to_facebook,publish_to_instagram, publish_to_linkedin, get_facebook_auth_url, exchange_code_for_access_token,extend_to_long_lived_token, fetch_user_pages
from django.shortcuts import redirect
from models import SocialPage

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


class PublishToInstagramView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id, *args, **kwargs):
        try:
            post = Post.objects.get(id=post_id)

            if post.client != request.user and not request.user.is_staff:
                return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

            page = post.platform_page or SocialPage.objects.filter(user=post.client, platform='facebook').first()

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

class PublishToLinkedInView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id, *args, **kwargs):
        try:
            post = Post.objects.get(id=post_id)

            if post.client != request.user and not request.user.is_staff:
                return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

            page = post.platform_page or SocialPage.objects.filter(user=post.client, platform='linkedin').first()

            if not page or not page.is_token_valid():
                return Response({"error": "Invalid or missing LinkedIn page token."}, status=400)

            li_post_id = publish_to_linkedin(post, page)

            post.linkedin_post_id = li_post_id
            post.status = "published"
            post.save()

            return Response({"success": True, "linkedin_post_id": li_post_id}, status=200)

        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
        



class FacebookConnectView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        auth_url = get_facebook_auth_url()
        return redirect(auth_url)


class FacebookCallbackView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        code = request.query_params.get("code")
        if not code:
            return Response({"error": "Missing authorization code"}, status=400)

        try:
            short_token = exchange_code_for_access_token(code)
            long_token = extend_to_long_lived_token(short_token)
            pages = fetch_user_pages(long_token)

            # Let the user select one or auto-save the first
            if not pages:
                return Response({"error": "No Facebook Pages found."}, status=400)

            page = pages[0]  # You can loop this if multi-page support is needed

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
        deleted, _ = SocialPage.objects.filter(user=request.user, platform="facebook").delete()
        return Response({"disconnected": deleted > 0})

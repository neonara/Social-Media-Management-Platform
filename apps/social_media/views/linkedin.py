import requests
import logging  # Add logging import
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import redirect

from apps.social_media.models import SocialPage
from apps.social_media.serializers import SocialPageSerializer
from apps.social_media.services import publish_to_linkedin
from apps.content.models import Post
from django.conf import settings
from rest_framework import status

# Set up logger
logger = logging.getLogger(__name__)

# LinkedIn settings from settings.py
LI_REDIRECT_URI = settings.LINKEDIN_REDIRECT_URI
LI_CLIENT_ID = settings.LINKEDIN_CLIENT_ID
LI_CLIENT_SECRET = settings.LINKEDIN_CLIENT_SECRET
LI_SCOPES = settings.LINKEDIN_SCOPES

# LinkedIn Connection Views
class LinkedInConnectView(APIView):
    permission_classes = [AllowAny]  # Allow any user initially, we'll authenticate manually
    
    def get(self, request):
        # Check if the user is already authenticated
        if not request.user.is_authenticated:
            # Get token from query params if it's not in the Authorization header
            token = request.query_params.get('token')
            if token:
                # Authenticate with token from query params
                from rest_framework_simplejwt.tokens import AccessToken
                try:
                    # Decode the token to get the user ID
                    token_data = AccessToken(token)
                    user_id = token_data['user_id']
                    
                    # Get the user from the database
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    user = User.objects.get(id=user_id)
                    
                    # Set the user on the request
                    request.user = user
                except Exception as e:
                    # If token is invalid or user not found, return an error
                    return Response(
                        {"error": "Invalid authentication token"},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            else:
                # No token provided
                return Response(
                    {"error": "Authentication required"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
                
        # User is now authenticated, generate state parameter
        state = str(request.user.id)
        
        url = (
            f"https://www.linkedin.com/oauth/v2/authorization?"
            f"client_id={LI_CLIENT_ID}&redirect_uri={LI_REDIRECT_URI}&"
            f"scope={LI_SCOPES}&response_type=code&state={state}"
        )
        return redirect(url)

class LinkedInCallbackView(APIView):
    permission_classes = [AllowAny]  # Allow anonymous as the user might not be authenticated during callback
    authentication_classes = []  # Disable authentication for this view completely
    
    def get(self, request):
        # Get the code and state from query parameters (not headers)
        code = request.GET.get("code")  # Using request.GET for query parameters
        state = request.GET.get("state")
        
        if not code:
            logger.error("LinkedIn callback: Missing authorization code")
            return redirect("http://localhost:3000/settings?error=Missing_authorization_code")
        
        try:
            # Step 1: Exchange code for access token
            token_url = "https://www.linkedin.com/oauth/v2/accessToken"
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": LI_REDIRECT_URI,
                "client_id": LI_CLIENT_ID,
                "client_secret": LI_CLIENT_SECRET
            }
            
            # Make the token request
            token_response = requests.post(token_url, data=data)
            logger.info(f"LinkedIn token response status: {token_response.status_code}")
            
            token_res = token_response.json()
            logger.info(f"LinkedIn token response: {token_res}")
            
            access_token = token_res.get("access_token")
            
            if not access_token:
                logger.error("LinkedIn callback: Failed to retrieve access token")
                return redirect("http://localhost:3000/settings?error=Failed_to_retrieve_access_token")
                
            # Step 2: Get user profile info with expanded fields
            profile_url = "https://api.linkedin.com/v2/me?projection=(id,localizedFirstName,localizedLastName,profilePicture(displayImage~:playableStreams))"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            profile_response = requests.get(profile_url, headers=headers)
            logger.info(f"LinkedIn profile response status: {profile_response.status_code}")
            
            profile_res = profile_response.json()
            logger.info(f"LinkedIn profile data: {profile_res}")
            
            # Extract profile information
            linkedin_id = profile_res.get("id", "")
            first_name = profile_res.get("localizedFirstName", "")
            last_name = profile_res.get("localizedLastName", "")
            
            # Check if email scope was included and fetch email if available
            email_response = None
            try:
                email_url = "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))"
                email_response = requests.get(email_url, headers=headers)
                email_data = email_response.json()
                logger.info(f"LinkedIn email data: {email_data}")
                # Extract email if available
            except Exception as email_error:
                logger.warning(f"Could not fetch LinkedIn email: {str(email_error)}")
            
            logger.info(f"LinkedIn profile extracted data - ID: {linkedin_id}, Name: {first_name} {last_name}")
            
            try:
                # Check if state contains a valid user ID
                if state and state != "None":
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    user = User.objects.get(id=state)
                    
                    logger.info(f"Found user with ID {state}: {user.email}")
                    
                    # Create or update the SocialPage for this user
                    social_page, created = SocialPage.objects.update_or_create(
                        client=user,
                        platform="linkedin",
                        defaults={
                            "page_id": linkedin_id,
                            "page_name": f"{first_name} {last_name}",
                            "access_token": access_token,
                            "permissions": {"expires_in": token_res.get('expires_in', 0)}
                        }
                    )
                    
                    logger.info(f"SocialPage {'created' if created else 'updated'} - page_id: {social_page.page_id}, page_name: {social_page.page_name}")
                    
                    # Redirect to the settings page with success message
                    return redirect("http://localhost:3000/settings/?connection=success")
                else:
                    # No valid state, redirect with error
                    logger.error(f"LinkedIn callback: Invalid state parameter: {state}")
                    return redirect("http://localhost:3000/settings/?error=Invalid_state_parameter")
            except Exception as e:
                # Error while creating social page
                logger.error(f"LinkedIn callback: Error creating social page: {str(e)}")
                return redirect(f"http://localhost:3000/settings/?error=Failed_to_create_social_page:{str(e)}")
            
        except Exception as e:
            logger.error(f"LinkedIn callback: Unexpected error: {str(e)}")
            return redirect(f"http://localhost:3000/settings?error={str(e)}")

class LinkedInDisconnectView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        deleted, _ = SocialPage.objects.filter(client=request.user, platform="linkedin").delete()
        return Response({"disconnected": deleted > 0})

class LinkedInPageView(APIView):
    """
    Get LinkedIn page details for current user
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            page = SocialPage.objects.get(client=request.user, platform='linkedin')
            serializer = SocialPageSerializer(page)
            return Response(serializer.data)
        except SocialPage.DoesNotExist:
            # Return a 200 response with connected=False instead of 404
            return Response({
                'connected': False,
                'platform': 'linkedin',
                'message': 'No LinkedIn page connected'
            }, status=200)

class PublishToLinkedInView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id, *args, **kwargs):
        try:
            post = Post.objects.get(id=post_id)

            if post.client != request.user and not request.user.is_staff:
                return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

            page = post.platform_page or SocialPage.objects.filter(client=post.client, platform='linkedin').first()

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

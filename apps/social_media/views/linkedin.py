import requests
import logging
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
    permission_classes = [
        AllowAny
    ]  # Allow any user initially, we'll authenticate manually

    def get(self, request):
        # Check if the user is already authenticated
        if not request.user.is_authenticated:
            # Get token from query params if it's not in the Authorization header
            token = request.query_params.get("token")
            if token:
                # Authenticate with token from query params
                from rest_framework_simplejwt.tokens import AccessToken

                try:
                    # Decode the token to get the user ID
                    token_data = AccessToken(token)
                    user_id = token_data["user_id"]

                    # Get the user from the database
                    from apps.accounts.models import User

                    user = User.objects.get(id=user_id)

                    # Set the user on the request
                    request.user = user
                except Exception as e:
                    # If token is invalid or user not found, return an error
                    return Response(
                        {"error": "Invalid authentication token"},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
            else:
                # No token provided
                return Response(
                    {"error": "Authentication required"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        # User is now authenticated, generate state parameter
        state = str(request.user.id)

        # Check if we should update the profile picture
        update_profile = request.query_params.get("update_profile", "false")

        # Build the LinkedIn authorization URL
        # Include the update_profile parameter in the state to pass it through the OAuth flow
        full_state = (
            f"{state}:{update_profile}" if update_profile.lower() == "true" else state
        )

        url = (
            f"https://www.linkedin.com/oauth/v2/authorization?"
            f"client_id={LI_CLIENT_ID}&redirect_uri={LI_REDIRECT_URI}&"
            f"scope={LI_SCOPES}&response_type=code&state={full_state}"
        )

        # Log the generated URL for debugging
        logger.info(f"Generated LinkedIn OAuth URL: {url}")
        logger.info(f"LinkedIn Client ID: {LI_CLIENT_ID}")
        logger.info(f"LinkedIn Redirect URI: {LI_REDIRECT_URI}")
        logger.info(f"LinkedIn Scopes: {LI_SCOPES}")

        return redirect(url)


class LinkedInCallbackView(APIView):
    permission_classes = [
        AllowAny
    ]  # Allow anonymous as the user might not be authenticated during callback
    authentication_classes = []  # Disable authentication for this view completely

    def get(self, request):
        # Log all incoming parameters for debugging
        logger.info(f"LinkedIn callback received parameters: {dict(request.GET)}")
        logger.info(f"LinkedIn callback full URL: {request.build_absolute_uri()}")

        # Get the code and state from query parameters (not headers)
        code = request.GET.get("code")  # Using request.GET for query parameters
        state = request.GET.get("state")
        error = request.GET.get("error")
        error_description = request.GET.get("error_description")

        # Check for OAuth error first
        if error:
            logger.error(f"LinkedIn OAuth error: {error} - {error_description}")
            return redirect(
                f"http://localhost:3000/settings?error=LinkedIn_OAuth_error:{error_description or error}"
            )

        if not code:
            logger.error("LinkedIn callback: Missing authorization code")
            logger.error(f"Available parameters: {list(request.GET.keys())}")
            return redirect(
                "http://localhost:3000/settings?error=Missing_authorization_code"
            )

        try:
            # Step 1: Exchange code for access token
            token_url = "https://www.linkedin.com/oauth/v2/accessToken"
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": LI_REDIRECT_URI,
                "client_id": LI_CLIENT_ID,
                "client_secret": LI_CLIENT_SECRET,
            }

            # Make the token request
            token_response = requests.post(token_url, data=data)
            logger.info(f"LinkedIn token response status: {token_response.status_code}")

            token_res = token_response.json()
            logger.info(f"LinkedIn token response: {token_res}")

            access_token = token_res.get("access_token")

            if not access_token:
                logger.error("LinkedIn callback: Failed to retrieve access token")
                return redirect(
                    "http://localhost:3000/settings?error=Failed_to_retrieve_access_token"
                )

            # Step 2: Get user profile using the OpenID Connect userinfo endpoint
            # This is the recommended endpoint for getting profile information in the OIDC flow
            userinfo_url = "https://api.linkedin.com/v2/userinfo"
            headers = {"Authorization": f"Bearer {access_token}"}

            profile_response = requests.get(userinfo_url, headers=headers)
            logger.info(
                f"LinkedIn userinfo response status: {profile_response.status_code}"
            )

            profile_res = profile_response.json()
            logger.info(f"LinkedIn userinfo data: {profile_res}")

            # Extract profile information from the OIDC userinfo response
            logger.info(
                f"Extracting LinkedIn profile data from userinfo response: {profile_res}"
            )
            linkedin_id = profile_res.get(
                "sub", ""
            )  # 'sub' is the user identifier in OIDC
            first_name = profile_res.get("given_name", "")  # OIDC uses given_name
            last_name = profile_res.get("family_name", "")  # OIDC uses family_name
            profile_picture = profile_res.get("picture", "")

            # Log detailed profile extraction
            logger.info(f"Extracted LinkedIn ID: '{linkedin_id}'")
            logger.info(f"Extracted first name: '{first_name}'")
            logger.info(f"Extracted last name: '{last_name}'")

            # Check if any key data is missing
            if not linkedin_id:
                logger.error("LinkedIn profile ID is missing from API response")
            if not first_name and not last_name:
                logger.warning("LinkedIn profile name is missing from API response")

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

            logger.info(
                f"LinkedIn profile extracted data - ID: {linkedin_id}, Name: {first_name} {last_name}"
            )

            try:
                # Check if state contains a valid user ID and possibly update_profile param
                if state and state != "None":
                    # Extract user ID and potentially update_profile flag from state
                    update_profile = "false"
                    if ":" in state:
                        state_parts = state.split(":", 1)
                        state = state_parts[0]
                        update_profile = state_parts[1]

                    from apps.accounts.models import User

                    user = User.objects.get(id=state)

                    # Store update_profile in request.GET for later use
                    request.GET = request.GET.copy()
                    request.GET["update_profile"] = update_profile

                    logger.info(f"Found user with ID {state}: {user.email}")

                    # Create or update the SocialPage for this user

                    # Check if we have a valid LinkedIn ID
                    if not linkedin_id:
                        logger.error(
                            "LinkedIn ID is missing from the response - cannot create SocialPage"
                        )
                        return redirect(
                            "http://localhost:3000/settings/?error=LinkedIn_profile_data_incomplete"
                        )

                    # Prepare the name - use available data or fallback to default
                    page_name = (
                        f"{first_name} {last_name}"
                        if first_name or last_name
                        else "LinkedIn User"
                    )
                    logger.info(f"Using page_name: '{page_name}' for LinkedIn page")

                    # Store the LinkedIn ID with the proper URN format required by LinkedIn API
                    linkedin_urn = f"urn:li:person:{linkedin_id}"
                    logger.info(f"Using LinkedIn URN: '{linkedin_urn}' for page_id")

                    # Store additional profile info if available
                    extra_permissions = {
                        "expires_in": token_res.get("expires_in", 0),
                        "profile_picture": profile_picture,
                    }

                    logger.info(
                        f"Creating/updating LinkedIn SocialPage with: ID={linkedin_urn}, Name={page_name}"
                    )
                    social_page, created = SocialPage.objects.update_or_create(
                        client=user,
                        platform="linkedin",
                        defaults={
                            "page_id": linkedin_urn,  # Store the full URN instead of just the ID
                            "page_name": page_name,
                            "access_token": access_token,
                            "permissions": extra_permissions,
                        },
                    )

                    # Update user information from LinkedIn profile data
                    user_updated = False

                    # Update user's first name from LinkedIn only if it's empty
                    if first_name and (not user.first_name or user.first_name == ""):
                        user.first_name = first_name
                        user_updated = True
                        logger.info(f"Updated user first name to '{first_name}'")
                    else:
                        logger.info(
                            f"User already has first name set: '{user.first_name}', not updating from LinkedIn"
                        )

                    # Update user's last name from LinkedIn only if it's empty
                    if last_name and (not user.last_name or user.last_name == ""):
                        user.last_name = last_name
                        user_updated = True
                        logger.info(f"Updated user last name to '{last_name}'")
                    else:
                        logger.info(
                            f"User already has last name set: '{user.last_name}', not updating from LinkedIn"
                        )

                    # Update user's profile picture if available and if user doesn't have one yet
                    if profile_picture and not user.user_image:
                        try:
                            logger.info(
                                f"Downloading profile picture from LinkedIn: {profile_picture}"
                            )
                            import urllib.request
                            from django.core.files import File
                            from django.core.files.temp import NamedTemporaryFile
                            import os

                            # Download the profile picture
                            img_temp = NamedTemporaryFile(delete=True)
                            urllib.request.urlretrieve(profile_picture, img_temp.name)

                            # Save it to the user model
                            file_name = f"linkedin_profile_{user.id}.jpg"
                            user.user_image.save(file_name, File(img_temp))
                            user_updated = True
                            logger.info(
                                f"Successfully updated user profile picture from LinkedIn for user {user.id}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to download LinkedIn profile picture: {str(e)}"
                            )
                    elif profile_picture:
                        logger.info(
                            f"User already has a profile picture, not updating from LinkedIn for user {user.id}"
                        )
                    else:
                        logger.info(
                            f"No profile picture available from LinkedIn for user {user.id}"
                        )

                    # Save user model if any field was updated
                    if user_updated:
                        user.save()
                        logger.info(
                            f"Updated user profile with LinkedIn data for user ID {user.id}"
                        )

                        # Simply clear the user cache - it will be regenerated fresh on next API call
                        from apps.accounts.services import clear_user_cache

                        clear_user_cache(user.id)
                        logger.info(
                            f"Cleared cache for user ID {user.id} - fresh data will be cached on next request"
                        )
                    else:
                        logger.info(
                            f"No user profile updates needed for user ID {user.id}"
                        )

                    logger.info(
                        f"SocialPage {'created' if created else 'updated'} - page_id: {social_page.page_id}, page_name: {social_page.page_name}"
                    )

                    # Redirect to the settings page with success message
                    return redirect(
                        "http://localhost:3000/settings/?connection=success"
                    )
                else:
                    # No valid state, redirect with error
                    logger.error(f"LinkedIn callback: Invalid state parameter: {state}")
                    return redirect(
                        "http://localhost:3000/settings/?error=Invalid_state_parameter"
                    )
            except Exception as e:
                # Error while creating social page
                logger.error(f"LinkedIn callback: Error creating social page: {str(e)}")
                return redirect(
                    f"http://localhost:3000/settings/?error=Failed_to_create_social_page:{str(e)}"
                )

        except Exception as e:
            logger.error(f"LinkedIn callback: Unexpected error: {str(e)}")
            return redirect(f"http://localhost:3000/settings?error={str(e)}")


class LinkedInDisconnectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        deleted, _ = SocialPage.objects.filter(
            client=request.user, platform="linkedin"
        ).delete()

        # Clear user cache to ensure frontend gets the latest data after disconnecting
        from apps.accounts.services import get_cached_user_data

        get_cached_user_data(request.user, force_refresh=True)

        return Response({"disconnected": deleted > 0})


class LinkedInPageView(APIView):
    """
    Get LinkedIn page details for current user
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            page = SocialPage.objects.get(client=request.user, platform="linkedin")
            serializer = SocialPageSerializer(page)
            return Response(serializer.data)
        except SocialPage.DoesNotExist:
            # Return a 200 response with connected=False instead of 404
            return Response(
                {
                    "connected": False,
                    "platform": "linkedin",
                    "message": "No LinkedIn page connected",
                },
                status=200,
            )


class PublishToLinkedInView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id, *args, **kwargs):
        try:
            post = Post.objects.get(id=post_id)

            if post.client != request.user and not request.user.is_staff:
                return Response(
                    {"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN
                )

            page = (
                post.platform_page
                or SocialPage.objects.filter(
                    client=post.client, platform="linkedin"
                ).first()
            )

            if not page or not page.is_token_valid():
                return Response(
                    {"error": "Invalid or missing LinkedIn page token."}, status=400
                )

            li_post_id = publish_to_linkedin(post, page)

            post.linkedin_post_id = li_post_id
            post.status = "published"
            post.save()

            return Response(
                {"success": True, "linkedin_post_id": li_post_id}, status=200
            )

        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

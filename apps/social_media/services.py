import json
import requests

from django.conf import settings

FB_APP_ID = settings.FACEBOOK_APP_ID
FB_REDIRECT_URI = settings.FACEBOOK_REDIRECT_URI
GRAPH_API_VERSION = settings.FACEBOOK_GRAPH_API_VERSION


def exchange_code_for_access_token(code):
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/oauth/access_token"
    params = {
        "client_id": FB_APP_ID,
        "redirect_uri": FB_REDIRECT_URI,
        "client_secret": settings.FACEBOOK_APP_SECRET,
        "code": code,
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()["access_token"]


def extend_to_long_lived_token(short_token):
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": FB_APP_ID,
        "client_secret": settings.FACEBOOK_APP_SECRET,
        "fb_exchange_token": short_token,
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()["access_token"]


def fetch_user_pages(long_token):
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/accounts"
    response = requests.get(url, params={"access_token": long_token})
    response.raise_for_status()
    return response.json()["data"]


# publish


def publish_to_facebook(post, page):
    url = f"https://graph.facebook.com/{page.page_id}/feed"
    payload = {"message": post.description, "access_token": page.access_token}
    response = requests.post(url, data=payload)
    if response.ok:
        return response.json().get("id")
    raise Exception(f"Facebook error: {response.text}")


def get_instagram_id(page):
    response = requests.get(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page.page_id}?fields=instagram_business_account&access_token={page.access_token}"
    )
    if response.ok:
        return response.json().get("instagram_business_account", {}).get("id")
    return None


def publish_to_instagram(post, page):
    ig_id = get_instagram_id(page)
    if not ig_id:
        raise Exception("Instagram account not linked.")

    media_url = post.media[0] if post.media else None
    if not media_url:
        raise Exception("No media URL found for Instagram.")

    create_media = requests.post(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_id}/media",
        data={
            "image_url": media_url,
            "caption": post.description,
            "access_token": page.access_token,
        },
    )
    if not create_media.ok:
        raise Exception(f"Instagram Media Creation Failed: {create_media.text}")

    creation_id = create_media.json()["id"]

    publish = requests.post(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_id}/media_publish",
        data={"creation_id": creation_id, "access_token": page.access_token},
    )
    if publish.ok:
        return publish.json()["id"]
    raise Exception(f"Instagram Publishing Failed: {publish.text}")


def publish_to_linkedin(post, page):
    """
    Publish a post to LinkedIn.
    Handles both text-only posts and posts with media.
    """
    import logging

    logger = logging.getLogger(__name__)

    headers = {
        "Authorization": f"Bearer {page.access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    logger.info(f"Publishing to LinkedIn with page_id: {page.page_id}")

    # IMPORTANT: For LinkedIn, the page_id stored should already be the full URN
    # If it's not, we'll need to prepend the URN prefix

    # Check if the page_id already contains the URN prefix
    if page.page_id.startswith("urn:li:"):
        author = page.page_id
        logger.info(f"Using provided URN as author: {author}")
    else:
        # If the ID is just numeric or from OIDC (sub field), we need to create a proper URN
        try:
            # Get current user info from userinfo endpoint (OpenID Connect)
            userinfo_url = "https://api.linkedin.com/v2/userinfo"
            profile_check = requests.get(userinfo_url, headers=headers)

            if profile_check.status_code == 200:
                # Successfully got profile info from OpenID userinfo endpoint
                profile_data = profile_check.json()
                # Use the 'sub' field from the OIDC response as the user identifier
                person_id = profile_data.get("sub", page.page_id)
                author = f"urn:li:person:{person_id}"

                logger.info(f"Using LinkedIn author URN from userinfo: {author}")
            else:
                # Fallback if we can't determine profile type
                author = f"urn:li:person:{page.page_id}"

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error determining LinkedIn author type: {str(e)}")
            # Default to person URN as fallback
            author = f"urn:li:person:{page.page_id}"

    # Check if the post has media attached
    has_media = post.media.exists()

    if not has_media:
        # Text-only post
        content = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": post.description or ""},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"LinkedIn post request: {content}")

        response = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            json=content,  # Using json parameter instead of data=json.dumps()
        )

        if response.ok:
            logger.info(f"LinkedIn post successful: {response.json()}")
            return response.json().get("id")

        logger.error(f"LinkedIn post failed: {response.text}")
        raise Exception(f"LinkedIn error: {response.text}")
    else:
        # Post with media
        # Get the first image from the post
        media_file = post.media.first()
        if media_file and media_file.file:
            media_url = media_file.file.url
            # If the URL is relative, convert to absolute URL
            if media_url.startswith("/"):
                from django.conf import settings

                # Use the domain from the ALLOWED_HOSTS setting
                domain = (
                    settings.ALLOWED_HOSTS[0]
                    if settings.ALLOWED_HOSTS
                    else "localhost:8000"
                )
                protocol = "https" if not settings.DEBUG else "http"
                media_url = f"{protocol}://{domain}{media_url}"

            # Create a media asset
            content = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": author,
                    "serviceRelationships": [
                        {
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent",
                        }
                    ],
                }
            }

            # Register the upload
            upload_response = requests.post(
                "https://api.linkedin.com/v2/assets?action=registerUpload",
                headers=headers,
                json=content,
            )

            if not upload_response.ok:
                raise Exception(
                    f"LinkedIn media registration error: {upload_response.text}"
                )

            upload_data = upload_response.json()
            asset_id = upload_data.get("value", {}).get("asset")
            upload_url = (
                upload_data.get("value", {})
                .get("uploadMechanism", {})
                .get("com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {})
                .get("uploadUrl")
            )

            if not asset_id or not upload_url:
                raise Exception("LinkedIn didn't provide upload URL or asset ID")

            # Download the image from the URL
            image_response = requests.get(media_url)
            if not image_response.ok:
                raise Exception(f"Failed to download image from {media_url}")

            # Upload the image to LinkedIn's upload URL
            upload_image_response = requests.put(
                upload_url,
                data=image_response.content,
                headers={"Authorization": f"Bearer {page.access_token}"},
            )

            if not upload_image_response.ok:
                raise Exception(
                    f"LinkedIn image upload error: {upload_image_response.text}"
                )

            # Create a share with the uploaded image
            share_content = {
                "author": author,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": post.description or ""},
                        "shareMediaCategory": "IMAGE",
                        "media": [
                            {
                                "status": "READY",
                                "description": {"text": post.title or ""},
                                "media": asset_id,
                                "title": {"text": post.title or ""},
                            }
                        ],
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }

            import logging

            logger = logging.getLogger(__name__)
            logger.info(f"LinkedIn image post request: {share_content}")

            share_response = requests.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers=headers,
                json=share_content,
            )

            if share_response.ok:
                logger.info(f"LinkedIn image post successful: {share_response.json()}")
                return share_response.json().get("id")

            logger.error(f"LinkedIn image post failed: {share_response.text}")
            raise Exception(f"LinkedIn share error: {share_response.text}")

        # If we get here, there was media but we couldn't process it
        # Fall back to a text-only post
        content = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": post.description or ""},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"LinkedIn fallback post request: {content}")

        response = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            json=content,  # Using json parameter instead of data=json.dumps()
        )

        if response.ok:
            logger.info(f"LinkedIn fallback post successful: {response.json()}")
            return response.json().get("id")

        logger.error(f"LinkedIn fallback post failed: {response.text}")
        raise Exception(f"LinkedIn error: {response.text}")

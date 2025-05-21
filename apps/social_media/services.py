import json
import requests

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
        "code": code
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
    payload = {
        "message": post.description,
        "access_token": page.access_token
    }
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
            "access_token": page.access_token
        }
    )
    if not create_media.ok:
        raise Exception(f"Instagram Media Creation Failed: {create_media.text}")

    creation_id = create_media.json()["id"]

    publish = requests.post(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_id}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": page.access_token
        }
    )
    if publish.ok:
        return publish.json()["id"]
    raise Exception(f"Instagram Publishing Failed: {publish.text}")


def publish_to_linkedin(post, page):
    headers = {
        "Authorization": f"Bearer {page.access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    content = {
        "author": f"urn:li:organization:{page.page_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": post.description or ''},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }

    response = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=headers,
        data=json.dumps(content)
    )

    if response.ok:
        return response.json().get("id")
    raise Exception(f"LinkedIn error: {response.text}")

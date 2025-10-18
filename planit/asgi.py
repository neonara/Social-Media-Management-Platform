import os

# Updated project name to 'planit'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'planit.settings')
import django
django.setup()  # ← This line is crucial when doing custom imports (like TokenAuthMiddleware)

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from planit.websocket_auth import TokenAuthMiddlewareStack
from django.conf import settings
from django.urls import re_path
from django.views.static import serve

# Import routing configurations from all apps
import apps.notifications.routing
import apps.collaboration.routing
import apps.content.routing
from apps.accounts.routing import websocket_urlpatterns as accounts_websocket_urlpatterns


# Combine WebSocket URL patterns from all apps
all_websocket_urlpatterns = (
    apps.notifications.routing.websocket_urlpatterns +
    apps.collaboration.routing.websocket_urlpatterns +
    apps.content.routing.websocket_urlpatterns +
    accounts_websocket_urlpatterns
)
print("ASGI setup - loading application")

print("TokenAuthMiddleware activated")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        TokenAuthMiddlewareStack(
            URLRouter(all_websocket_urlpatterns)
        )
    ),
})
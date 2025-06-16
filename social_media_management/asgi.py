import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_management.settings')
import django
django.setup()  # ← This line is crucial when doing custom imports (like TokenAuthMiddleware)

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from social_media_management.websocket_auth import TokenAuthMiddlewareStack

# Import routing configurations from all apps
import apps.notifications.routing
import apps.collaboration.routing
from apps.accounts.routing import websocket_urlpatterns as accounts_websocket_urlpatterns


# Combine WebSocket URL patterns from all apps
all_websocket_urlpatterns = (
    apps.notifications.routing.websocket_urlpatterns +
    apps.collaboration.routing.websocket_urlpatterns +
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
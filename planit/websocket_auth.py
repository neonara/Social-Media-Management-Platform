from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import urllib.parse


class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # Import inside the method to avoid AppRegistryNotReady error
        from django.contrib.auth.models import AnonymousUser
        from apps.accounts.models import User

        scope["user"] = AnonymousUser()

        # Get the token from query string
        query_string = scope.get("query_string", b"").decode()
        client_info = scope.get("client", ["unknown", 0])
        client_ip = client_info[0] if client_info else "unknown"

        if query_string:
            try:
                query_params = dict(urllib.parse.parse_qsl(query_string))
                token = query_params.get("token", "")  # <-- FIXED
                print(
                    f"WebSocket auth attempt from {client_ip}: Token present: {bool(token)}"
                )
                if token:
                    access_token = AccessToken(token)
                    user_id = access_token.payload.get("user_id")
                    if user_id:
                        user = await self.get_user(user_id, User)
                        if user and not user.is_anonymous:
                            scope["user"] = user
                            print(
                                f"WebSocket auth success: User {user_id} ({user.email}) authenticated"
                            )
                        else:
                            print(f"WebSocket auth failed: User {user_id} not found")
                    else:
                        print("WebSocket auth failed: No user_id in token payload")
                else:
                    print(
                        f"WebSocket auth failed from {client_ip}: No token in query params"
                    )
            except (InvalidToken, TokenError) as e:
                print(f"WebSocket auth failed from {client_ip}: Invalid token - {e}")
            except (ValueError, UnicodeDecodeError) as e:
                print(
                    f"WebSocket auth failed from {client_ip}: Query string parsing error - {e}"
                )
        else:
            print(f"WebSocket connection from {client_ip}: No query string provided")

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user(self, user_id, User):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            from django.contrib.auth.models import AnonymousUser

            return AnonymousUser()


def TokenAuthMiddlewareStack(inner):
    return TokenAuthMiddleware(inner)

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import urllib.parse

class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # Import inside the method to avoid AppRegistryNotReady error
        from django.contrib.auth.models import AnonymousUser
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        scope['user'] = AnonymousUser()
        
        # Get the token from query string
        query_string = scope.get('query_string', b'').decode()
        
        if query_string:
            try:
                query_params = dict(urllib.parse.parse_qsl(query_string))
                token = query_params.get('token', '')  # <-- FIXED
                print("TOKEN:", (token != None))
                if token:
                    access_token = AccessToken(token)
                    user_id = access_token.payload.get('user_id')
                    if user_id:
                        user = await self.get_user(user_id, User)
                        scope['user'] = user
            except (InvalidToken, TokenError, ValueError, UnicodeDecodeError):
                pass

        
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
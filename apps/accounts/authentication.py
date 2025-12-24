from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework import exceptions

from apps.accounts.models import User


class JWTCookieAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that reads tokens from cookies instead of headers.
    Provides enhanced security by validating tokens properly and preventing
    manual cookie manipulation.
    """

    def authenticate(self, request):
        """
        Authenticate the request by checking for a valid JWT token in cookies.
        """
        # Get token from cookies
        raw_token = request.COOKIES.get("access_token")

        if raw_token is None:
            return None

        # Validate the token
        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)

        # Additional security checks
        if not self.is_user_valid(user):
            raise exceptions.AuthenticationFailed("User account is invalid.")

        return (user, validated_token)

    def get_validated_token(self, raw_token):
        """
        Validates the token and ensures it's not tampered with.
        """
        try:
            # Use UntypedToken for initial validation
            UntypedToken(raw_token)
            # Then use the parent's validation for full JWT validation
            return super().get_validated_token(raw_token)
        except TokenError as e:
            raise exceptions.AuthenticationFailed(f"Invalid token: {str(e)}")

    def get_user(self, validated_token):
        """
        Get user from the validated token with additional security checks.
        """
        try:
            user_id = validated_token.get("user_id")
            if user_id is None:
                raise exceptions.AuthenticationFailed(
                    "Token contained no recognizable user identification"
                )

            user = User.objects.get(id=user_id)

            # Verify user is still active and verified
            if not user.is_active:
                raise exceptions.AuthenticationFailed("User account is disabled.")

            if not user.is_verified:
                raise exceptions.AuthenticationFailed("User email is not verified.")

            return user

        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed("User not found.")
        except Exception as e:
            raise exceptions.AuthenticationFailed(f"Authentication failed: {str(e)}")

    def is_user_valid(self, user):
        """
        Additional validation to ensure user account integrity.
        """
        if not user or user.is_anonymous:
            return False

        # Check if user account is still valid
        if not user.is_active or not user.is_verified:
            return False

        return True


class JWTHeaderAuthentication(JWTAuthentication):
    """
    Standard JWT authentication from Authorization header with enhanced validation.
    """

    def authenticate(self, request):
        """
        Authenticate using Authorization header with additional security checks.
        """
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)

        # Additional security checks
        if not self.is_user_valid(user):
            raise exceptions.AuthenticationFailed("User account is invalid.")

        return (user, validated_token)

    def get_user(self, validated_token):
        """
        Get user from the validated token with additional security checks.
        """
        try:
            user_id = validated_token.get("user_id")
            if user_id is None:
                raise exceptions.AuthenticationFailed(
                    "Token contained no recognizable user identification"
                )

            user = User.objects.get(id=user_id)

            # Verify user is still active and verified
            if not user.is_active:
                raise exceptions.AuthenticationFailed("User account is disabled.")

            if not user.is_verified:
                raise exceptions.AuthenticationFailed("User email is not verified.")

            return user

        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed("User not found.")
        except Exception as e:
            raise exceptions.AuthenticationFailed(f"Authentication failed: {str(e)}")

    def is_user_valid(self, user):
        """
        Additional validation to ensure user account integrity.
        """
        if not user or user.is_anonymous:
            return False

        # Check if user account is still valid
        if not user.is_active or not user.is_verified:
            return False

        return True


class SecurityMiddleware:
    """
    Security middleware to add additional protection against token manipulation.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log suspicious authentication attempts
        access_token = request.COOKIES.get("access_token")
        auth_header = request.META.get("HTTP_AUTHORIZATION")

        # Log if both cookie and header tokens exist (potential attack)
        if access_token and auth_header:
            # Log this as a potential security issue
            import logging

            logger = logging.getLogger("security")
            logger.warning(
                f'Dual authentication attempt from {request.META.get("REMOTE_ADDR")}: '
                f"Both cookie and header tokens present"
            )

        response = self.get_response(request)
        return response

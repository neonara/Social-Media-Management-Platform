from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import AuthenticationFailed
from .models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail

class UserLoginSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=155, min_length=6)
    password = serializers.CharField(max_length=68, write_only=True)
    full_name = serializers.CharField(max_length=255, read_only=True)
    access_token = serializers.CharField(max_length=255, read_only=True)
    refresh_token = serializers.CharField(max_length=255, read_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'password', 'full_name', 
            'access_token', 'refresh_token', 
            'is_administrator', 'is_moderator', 
            'is_community_manager', 'is_client'
        ]

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        request = self.context.get('request')

        user = authenticate(request, email=email, password=password)

        if not user:
            raise AuthenticationFailed("Invalid credentials. Please try again.")

        if not user.is_verified:
            raise AuthenticationFailed("Email is not verified.")

        if not user.is_active:  
            raise AuthenticationFailed("Your account is inactive. Contact support.")

        refresh = RefreshToken.for_user(user)
        tokens = {
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
        }

        return {
            'email': user.email,
            'full_name': user.get_full_name(),
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'is_administrator': user.is_administrator,
            'is_moderator': user.is_moderator,
            'is_community_manager': user.is_community_manager,
            'is_client': user.is_client,
        }

class LogoutUserSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh_token']
        return attrs

    def save(self, **kwargs):
        try:
            token = RefreshToken(self.token)
            token.blacklist()  
            
        except Exception as e:
            raise serializers.ValidationError("Invalid token")
        
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        
        return value

    def send_reset_email(self):
        email = self.validated_data["email"]
        user = User.objects.get(email=email)
        token = PasswordResetTokenGenerator().make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_link = f"http://127.0.0.1:8000/api/auth/reset-password-confirm/{uid}/{token}/"

        send_mail(
            "Password Reset Request",
            f"Click the link below to reset your password:\n\n{reset_link}",
            "noreply@yourapp.com",
            [email],
            fail_silently=False,
        )

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        try:
            uid = force_str(urlsafe_base64_decode(data["uid"]))
            user = User.objects.get(pk=uid)

            if not PasswordResetTokenGenerator().check_token(user, data["token"]):
                raise serializers.ValidationError("Invalid or expired token.")

        except (User.DoesNotExist, ValueError, TypeError):
            raise serializers.ValidationError("Invalid user or token.")

        return {"user": user, "new_password": data["new_password"]}

    def save(self):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save()


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['email', 'password', 'is_administrator', 'is_moderator', 'is_community_manager', 'is_client', 'is_verified']

    def validate(self, data):
        """Ensure only one role is set to True."""
        roles = ['is_administrator', 'is_moderator', 'is_community_manager', 'is_client']
        role_values = [data.get(role, False) for role in roles]

        if sum(role_values) > 1:
            raise serializers.ValidationError("A user can only have one role at a time.")
        
        return data

    def update(self, instance, validated_data):
        """Update user details, ensuring password is hashed if provided."""
        password = validated_data.pop('password', None)

        if password:
            instance.set_password(password)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
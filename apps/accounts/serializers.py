from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import AuthenticationFailed
from .models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator

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
        
class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=155, min_length=6)

    class Meta:
        fields = ['email']

    def validate(self, attrs):
        email = attrs.get('email')
        user = User.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError("Invalid email")
        if not user.is_verified:  
            raise serializers.ValidationError("Email is not verified")
        uid64 = user.id
        token = PasswordResetTokenGenerator().make_token(user)
        reset_link = f'http://127.0.0.1:8000/api/auth/reset/{uid64}/{token}'  
        return {
            'reset_link': reset_link
        }
        
class SetNewPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=68, min_length=6, write_only=True)
    confirm_password = serializers.CharField(max_length=68, min_length=6, write_only=True)
    id = serializers.CharField(max_length=255)
    token = serializers.CharField(max_length=255)

    class Meta:
        fields = ['password', 'confirm_password', 'id', 'token']

    def validate(self, attrs):
        password = attrs.get('password')
        confirm_password = attrs.get('confirm_password')
        token = attrs.get('token')
        uid = attrs.get('id')

      
        if password != confirm_password:
            raise serializers.ValidationError("Passwords do not match")

        try:
            
            user = User.objects.get(id=uid)

          
            if not PasswordResetTokenGenerator().check_token(user, token):
                raise AuthenticationFailed("Invalid token", 401)

           
            user.set_password(password)
            user.save()
            return user

        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid user ID")
        except Exception as e:
            raise serializers.ValidationError("Invalid token or user ID")

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_password(data["old_password"]):
            raise serializers.ValidationError({"old_password": "Incorrect password"})
        return data
    



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
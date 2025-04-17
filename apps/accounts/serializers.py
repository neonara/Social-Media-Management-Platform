from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import AuthenticationFailed
from .models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from .utils.password_utils import generate_password
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail
from django.conf import settings

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
            'id'
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

class CreateUserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=155)
    role = serializers.ChoiceField(choices=[
        ('administrator', 'Administrator'),
        ('moderator', 'Moderator'),
        ('community_manager', 'Community Manager'),
        ('client', 'Client')
    ])

    class Meta:
        model = User
        fields = ['email', 'role']

    def validate_email(self, value):
        """
        Check if the email already exists in the system.
        """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def create(self, validated_data):
        email = validated_data['email']
        role = validated_data.pop('role', 'client')  # Default to client if not specified
        password = generate_password()

        self.password = password
        
        user = User.objects.create_user(
            email=email,
            password=password,
            is_active=True,
            is_verified=True
        )
        
        # Set the appropriate role based on the input
        if role == 'administrator':
            user.is_administrator = True
        elif role == 'moderator':
            user.is_moderator = True
        elif role == 'community_manager':
            user.is_community_manager = True
        elif role == 'client':
            user.is_client = True
        
        user.save()

        reset_link = f"{settings.FRONTEND_URL}/first-reset-password?email={email}"
        email_body = f"""
        Your account has been created.
        
        Email: {email}
        Temporary Password: {password}
        Role: {role.replace('_', ' ').title()}
        
        Please change your password by visiting:
        {reset_link}
        """

        try:
            send_mail(
                'Account Created - Social Media Management Platform',
                email_body,
                "achref.maarfi0@gmail.com",
                [email],
                fail_silently=False,
            )
        except Exception as e:
            # In development, just log the error and continue
            print(f"Email sending failed: {e}")
            # If using development console backend, print the temp password so you can test
            if hasattr(settings, 'DEBUG_EMAIL') and settings.DEBUG_EMAIL:
                print(f"DEV CREDENTIALS - Email: {email}, Password: {password}")

        return user

class FirstTimePasswordChangeSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)

    def validate(self, data):
        # Get user by email
        email = data.get('email')
        try:
            user = User.objects.get(email=email)
            # Store the user for save method
            self.user = user
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User not found."})

        if not user.check_password(data["password"]):
            raise serializers.ValidationError({"password": "Incorrect temporary password"})
        
        return data

    def save(self):
        # Use the stored user instance
        self.user.set_password(self.validated_data['new_password'])
        self.user.save()
        return self.user

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

class AssignModeratorSerializer(serializers.Serializer):
    moderator_id = serializers.IntegerField()

    def validate_moderator_id(self, value):
        try:
            moderator = User.objects.get(id=value, is_moderator=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("Moderator does not exist or is not a valid moderator.")
        return value

class AssigncommunityManagerstoModeratorsSerializer(serializers.Serializer):
    cm_id = serializers.IntegerField()

    def validate_cm_id(self, value):
        try:
            cm = User.objects.get(id=value, is_community_manager=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("Community Manager does not exist or is not a valid CM.")
        return value

class GetUserSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields = ['id', 'email', 'is_administrator', 'is_moderator', 'is_community_manager', 
                  'is_client', 'is_verified', 'phone_number', 'first_name', 'last_name', 'full_name']
        
        extra_kwargs = {
            'user_image': {'required': False},
            'email':{'required': False},
        }

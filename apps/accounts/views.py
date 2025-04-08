from .models import User
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from rest_framework.views import APIView

from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from .serializers import AdminUserUpdateSerializer, ChangePasswordSerializer, SetNewPasswordSerializer, UserLoginSerializer, CreateUserSerializer, FirstTimePasswordChangeSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.generics import UpdateAPIView
from rest_framework import generics, status
from rest_framework.response import Response
from .serializers import PasswordResetRequestSerializer, PasswordResetConfirmSerializer

class ListUsers(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.all()
        user_data = [
            {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "is_staff": user.is_staff,
            "roles": [
                role
                for role, has_role in {
                "administrator": user.is_administrator,
                "moderator": user.is_moderator,
                "community_manager": user.is_community_manager,
                "client": user.is_client,
                }.items()
                if has_role
            ],  # Dynamically include roles based on user attributes
            }
            for user in users
        ]
        return Response(user_data, status=status.HTTP_200_OK)

class CreateUserView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = CreateUserSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                
                # Get the password from the serializer
                password = getattr(serializer, 'password', None)
                
                response_data = {"message": "User created successfully"}
                
                # Include credentials in the API response for development
                if settings.DEBUG:
                    response_data.update({
                        "message": "DEVELOPMENT ONLY - Credentials for testing",
                        "email": user.email,
                        "password": password,
                        "reset_link": f"{settings.FRONTEND_URL}/first-reset-password?email={user.email}"
                    })
                
                return Response(response_data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response(
                    {"error": f"Failed to create user: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)   

class FirstTimePasswordChangeView(APIView):
    permission_classes = [AllowAny]  # Allow anyone to change first-time password

    def post(self, request):
        serializer = FirstTimePasswordChangeSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            new_password = serializer.validated_data['new_password']
            
            try:
                user = User.objects.get(email=email)
                
                # Print for debugging
                print(f"Attempting password change for {email}")
                print(f"Submitted temp password: {password}")
                
                # Check if the current password is correct
                if not user.check_password(password):
                    return Response(
                        {"password": ["Incorrect temporary password"]},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Set and save the new password
                user.set_password(new_password)
                user.save()
                
                # Generate tokens for the user
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'message': 'Password changed successfully',
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                }, status=status.HTTP_200_OK)
                
            except User.DoesNotExist:
                return Response(
                    {"email": ["User with this email does not exist"]},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLoginView(APIView):
    permission_classes = [AllowAny]  

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            response = Response(serializer.validated_data, status=status.HTTP_200_OK)
            response.set_cookie("access_token", serializer.validated_data["access_token"], httponly=True, samesite="Lax")  # Store token securely
            response.set_cookie("refresh_token", serializer.validated_data["refresh_token"], httponly=True, samesite="Lax")
            return response
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LogoutUserView(APIView):
    #permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')  # Read from cookies
        if not refresh_token:
            return Response({"error": "No refresh token found"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()  # Blacklist token
        except Exception:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

        response = Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)
        response.delete_cookie("access_token")  # Delete cookies
        response.delete_cookie("refresh_token")
        return response

class PasswordResetRequestView(APIView):
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        
        if serializer.is_valid():
            
            email = serializer.validated_data.get('email')  
            CodeUser = get_user_model()  
            user = CodeUser.objects.filter(email=email).first() 
            
            if not user:
                return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)

           
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"http://localhost:8000/api/auth/reset_password/{uidb64}/{token}/"

            
            subject = "Password Reset Request"
            message = f"Hi {user.username},\n\nClick the link below to reset your password:\n{reset_url}\n\nIf you didn't request this, ignore this email."
            send_mail(subject, message, "nbibaalae@gmail.com", [user.email])

            return Response({"message": "Password reset link sent to email."}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SetNewPasswordView(APIView):
    def post(self, request, uid64, token):
        data = request.data
        data['id'] = uid64
        data['token'] = token
        serializer = SetNewPasswordSerializer(data=data)
        if serializer.is_valid():
            return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data["new_password"])
            request.user.save()
            return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)

class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.send_reset_email()
            return Response({"message": "Password reset email sent."}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, uid, token):
        data = {"uid": uid, "token": token, "new_password": request.data.get("new_password")}
        serializer = self.get_serializer(data=data)
        
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Password reset successful."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminUpdateUserView(UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = AdminUserUpdateSerializer
    permission_classes = [IsAuthenticated] 
    lookup_field = 'user_id'
    lookup_url_kwargs = 'user_id'
    def put(self, request , user_id=None):
        """Custom update logic to handle user updates."""
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User updated successfully", "user": serializer.data}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def get_object(self):
       queryset = self.filter_queryset(self.get_queryset())
       obj = queryset.get(pk=self.kwargs['user_id'])
       self.check_object_permissions(self.request ,obj)
       return obj
    
class AdminDeleteUserView(APIView):
    permission_classes = [IsAdminUser]  # Only admin can delete users

    def delete(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
            email = user.email  # Store email before deletion for the response message
            user.delete()
            return Response(
                {'message': f'User with ID {user_id} (email: {email}) has been deleted successfully'},
                status=status.HTTP_200_OK  # Change to 200 OK so message is displayed
            )
        except User.DoesNotExist:
            return Response({"error": "User does not exist"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"Error deleting user: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
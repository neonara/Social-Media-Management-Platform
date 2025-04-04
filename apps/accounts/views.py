from .models import User
from django.contrib.auth.tokens import default_token_generator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny

from rest_framework.generics import UpdateAPIView
from .serializers import AdminUserUpdateSerializer, UserLoginSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import generics, status
from rest_framework.response import Response
from .serializers import PasswordResetRequestSerializer, PasswordResetConfirmSerializer


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
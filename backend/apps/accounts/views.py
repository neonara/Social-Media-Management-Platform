from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import PasswordResetSerializer, UserLoginSerializer
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from .serializers import LogoutUserSerializer
from .serializers import SetNewPasswordSerializer
from rest_framework_simplejwt.tokens import RefreshToken

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
            return Response({"reset_link": serializer.validated_data['reset_link']}, status=status.HTTP_200_OK)
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
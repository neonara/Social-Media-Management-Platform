from .models import User
from django.contrib.auth.tokens import default_token_generator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny

from rest_framework.generics import UpdateAPIView
from .serializers import AdminUserUpdateSerializer, UserLoginSerializer, AssignModeratorSerializer, AssigncommunityManagerstoModeratorsSerializer
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
   
class AssignModeratorToClientView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, client_id):
        if not request.user.is_administrator:
            return Response({"error": "Only administrators can assign moderators."}, status=403)

        try:
            client = User.objects.get(id=client_id, is_client=True)
        except User.DoesNotExist:
            return Response({"error": "Client not found."}, status=404)

        serializer = AssignModeratorSerializer(data=request.data)
        if serializer.is_valid():
            moderator_id = serializer.validated_data["moderator_id"]
            moderator = User.objects.get(id=moderator_id)

            client.assigned_moderator = moderator
            client.save()

            return Response({"message": f"Moderator {moderator.email} assigned to client {client.email}."})
        return Response(serializer.errors, status=400)
    
class AssignCommunityManagerToModeratorView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, moderator_id):
        if not request.user.is_administrator:
            return Response({"error": "Only administrators can assign community managers."}, status=403)

        try:
            moderator = User.objects.get(id=moderator_id, is_moderator=True)
        except User.DoesNotExist:
            return Response({"error": "Moderator not found."}, status=404)

        serializer = AssigncommunityManagerstoModeratorsSerializer(data=request.data)
        if serializer.is_valid():
            cm_id = serializer.validated_data["cm_id"]
            cm = User.objects.get(id=cm_id)

            moderator.assigned_communitymanagers = cm
            moderator.save()

            return Response({"message": f"community Manager {cm.email} assigned to moderator {moderator.email}."})
        return Response(serializer.errors, status=400)
    
class ManageAssignedCommunityManagerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        #View the assigned CM
    
        if not request.user.is_moderator:
            return Response({"error": "Only moderators can view assigned community managers."}, status=403)

        #get
        assigned_cm = request.user.assigned_communitymanagers
        if assigned_cm:
            return Response({
                "message": f"Assigned Community Manager: {assigned_cm.email}",
                "cm_id": assigned_cm.id,
                "cm_email": assigned_cm.email,
                "cm_name": f"{assigned_cm.first_name} {assigned_cm.last_name}",
            })
        else:
            return Response({"message": "No Community Manager assigned."}, status=404)

    def delete(self, request):
        #delete
        if not request.user.is_moderator:
            return Response({"error": "Only moderators can remove assigned community managers."}, status=403)
        assigned_cm = request.user.assigned_communitymanagers
        if not assigned_cm:
            return Response({"error": "No Community Manager assigned."}, status=404)
        request.user.assigned_communitymanagers = None
        request.user.save()

        return Response({"message": "Assigned Community Manager removed."})

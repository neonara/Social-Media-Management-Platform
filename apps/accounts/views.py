from .models import User
from django.conf import settings
from rest_framework.views import APIView
from django.core.mail import send_mail
from rest_framework.exceptions import PermissionDenied

from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser, BasePermission
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.generics import UpdateAPIView
from rest_framework import generics, status
from rest_framework.response import Response
from .serializers import PasswordResetRequestSerializer, PasswordResetConfirmSerializer, AssignModeratorSerializer, GetUserSerializer, UserLoginSerializer, CreateUserSerializer, FirstTimePasswordChangeSerializer ,AssigncommunityManagerstoModeratorsSerializer
from .services import get_cached_user_data  # Import the caching service
from django.core.cache import cache

class IsAdministrator(BasePermission):
    """Allows access only to administrators."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_administrator
    
class IsModerator(BasePermission):
    """Allows access only to administrators."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_moderator


class ListUsers(APIView):
    permission_classes = [IsAdministrator]  # Only authenticated users can access this view
    def get(self, request):
        users = User.objects.all()
        user_data = []

        for user in users:
            data = {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "phone_number": user.phone_number,

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
                ],
            }

          
            if user.is_client and user.assigned_moderator:
                data["assigned_moderator"] = user.assigned_moderator.full_name
            else:
                data["assigned_moderator"] = None

            
            if user.is_moderator:
                assigned_cms = user.assigned_communitymanagers.all()
                data["assigned_communitymanagers"] = ", ".join([cm.full_name for cm in assigned_cms]) if assigned_cms else None
            else:
                data["assigned_communitymanagers"] = None

            user_data.append(data)

        return Response(user_data, status=status.HTTP_200_OK)

class AssignedCMsToModeratorView(APIView):
    permission_classes = [IsModerator]

    def get(self, request):
        moderator = request.user
        assigned_cms = User.objects.filter(assigned_moderators=moderator)
        cm_data = []

        for cm in assigned_cms:
            data = {
                "id": cm.id,
                "full_name": cm.full_name,
                "email": cm.email,
                "phone_number": cm.phone_number,
                "is_active": cm.is_active,
                "is_staff": cm.is_staff,
                "roles": [
                    role
                    for role, has_role in {
                        "administrator": cm.is_administrator,
                        "moderator": cm.is_moderator,
                        "community_manager": cm.is_community_manager,
                        "client": cm.is_client,
                    }.items()
                    if has_role
                ],
                # Add any other relevant CM information you want to display
            }
            cm_data.append(data)

        return Response(cm_data, status=status.HTTP_200_OK)

class CreateUserView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = CreateUserSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                
                
                password = getattr(serializer, 'password', None)
                
                response_data = {"message": "User created successfully"}
                
               
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
    permission_classes = [IsAuthenticated]

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
    
class UpdateUserView(UpdateAPIView):
    queryset = User.objects.all()  # Add this line ✅
    serializer_class = GetUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        restricted_fields = {
            'is_administrator', 'is_moderator', 'is_community_manager',
            'is_client', 'is_staff', 'is_supplier', 'is_active',
            'is_superuser', 'is_verified'
        }
        for field in restricted_fields:
            if field in request.data:
                raise PermissionDenied(f"You are not allowed to modify the '{field}' field.")

        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        cache.delete(f"user_meta:{request.user.id}")
        
        return Response(serializer.data, status=status.HTTP_200_OK)

class GetUserByIdView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
            data = {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
                "email": user.email,
                "is_staff": user.is_staff,
                "is_administrator": user.is_administrator,
                "is_moderator": user.is_moderator,
                "is_community_manager": user.is_community_manager,
                "is_client": user.is_client,
            }
            
            # Add related information based on role
            if user.is_client and user.assigned_moderator:
                data["assigned_moderator"] = user.assigned_moderator.full_name
            elif user.is_moderator:
                assigned_cms = user.assigned_communitymanagers.all()
                data["assigned_communitymanagers"] = [
                    {"id": cm.id, "full_name": cm.full_name}
                    for cm in assigned_cms
                ] if assigned_cms else []
            
            return Response(data, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

class AssignModeratorToClientView(APIView):
    permission_classes = [IsAdministrator]  # <-- Everyone can access this view

    def put(self, request, client_id):
        try:
            client = User.objects.get(id=client_id, is_client=True)
        except User.DoesNotExist:
            return Response({"error": "Client not found."}, status=404)

        serializer = AssignModeratorSerializer(data=request.data)
        if serializer.is_valid():
            moderator_id = serializer.validated_data["moderator_id"]
            try:
                moderator = User.objects.get(id=moderator_id, is_moderator=True)
            except User.DoesNotExist:
                return Response({"error": "Moderator not found."}, status=404)

            client.assigned_moderator = moderator
            client.save()

            send_mail(
                'You have been assigned as a moderator',
                f'Hello {moderator.full_name},\n\nYou have been assigned as a moderator for client {client.full_name}. Please review the client details and take the necessary actions.\n\nBest regards,\nAdmin',
                settings.EMAIL_HOST_USER,
                [moderator.email],
                fail_silently=False,
            )

            return Response({"message": f"Moderator {moderator.email} assigned to client {client.email}."})

        return Response(serializer.errors, status=400)

class AssignCommunityManagerToModeratorView(APIView):
    permission_classes = [IsAdministrator]  

    def put(self, request, moderator_id):
        try:
            
            moderator = User.objects.get(id=moderator_id, is_moderator=True)
        except User.DoesNotExist:
            return Response({"error": "Moderator not found."}, status=404)

        serializer = AssigncommunityManagerstoModeratorsSerializer(data=request.data)
        if serializer.is_valid():
            cm_id = serializer.validated_data["cm_id"]
            try:
                cm = User.objects.get(id=cm_id, is_community_manager=True)
            except User.DoesNotExist:
                return Response({"error": "Community Manager not found."}, status=404)

            
            moderator.assigned_communitymanagers.add(cm)
            moderator.save()

            send_mail(
                'You have been assigned to a moderator',
                f'Hello {cm.full_name},\n\nYou have been assigned to Moderator {moderator.full_name}. Please review and collaborate.\n\nBest regards,\nAdmin',
                settings.EMAIL_HOST_USER,
                [cm.email],
                fail_silently=False,
            )

            return Response({"message": f"Community Manager {cm.email} assigned to Moderator {moderator.email}."})

        return Response(serializer.errors, status=400)

class RemoveCommunityManagerFromModeratorView(APIView):
     permission_classes = [IsAdministrator]  
     def delete(self, request, moderator_id, cm_id):
        try:
           
            moderator = User.objects.get(id=moderator_id, is_moderator=True)
            cm = User.objects.get(id=cm_id, is_community_manager=True)
            
            
            if cm in moderator.assigned_communitymanagers.all():
                moderator.assigned_communitymanagers.remove(cm)
                return Response({"message": "Community Manager unassigned from Moderator."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "This Community Manager is not assigned to this Moderator."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
class RemoveModeratorFromClientView(APIView):
    permission_classes = [IsAdministrator]  
    def delete(self, request, client_id):
        try:
            
            client = User.objects.get(id=client_id, is_client=True)
            
            
            if client.assigned_moderator is None:
                return Response({"message": "No moderator assigned to this client."}, status=status.HTTP_400_BAD_REQUEST)

           
            client.assigned_moderator = None
            client.save()
            return Response({"message": "Moderator unassigned from client."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "Client not found."}, status=status.HTTP_404_NOT_FOUND)

    
class AdminDeleteUserView(APIView):
    permission_classes = [IsAdministrator]  # Only admin can delete users

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
        

class FetchEmails(APIView):
    permission_classes = [IsAuthenticated, IsAdministrator]  # Only admin can fetch emails

    def get(self, request):
        # No need for additional check since IsAdministrator handles it
        users = User.objects.all()
        user_emails = [{"email": user.email} for user in users]
        return Response(user_emails, status=200)
    
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user_data = get_cached_user_data(request.user)  # Use cached data
        return Response(user_data)

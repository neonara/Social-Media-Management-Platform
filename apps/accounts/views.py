from apps.accounts.tasks import send_celery_email
from apps.accounts.models import User
from social_media_management import settings
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied

from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser, BasePermission
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.generics import UpdateAPIView
from rest_framework import generics, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator


from .serializers import PasswordResetRequestSerializer, PasswordResetConfirmSerializer, AssignModeratorSerializer, GetUserSerializer, UserLoginSerializer, CreateUserSerializer, FirstTimePasswordChangeSerializer ,AssigncommunityManagerstoModeratorsSerializer, RemoveCMsFromClientSerializer, AssignCMToClientSerializer, CreateCMSerializer

from .services import get_cached_user_data  # Import the caching service
from django.core.cache import cache
from apps.notifications.services import notify_user  # Import the notification service

#permissions
class IsAdministrator(BasePermission):
    """Allows access only to administrators."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_administrator
    
class IsModerator(BasePermission):
    """Allows access only to administrators."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_moderator

class IsAdminOrSuperAdmin(BasePermission):
    """Allows access only to moderators or administrators."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_superadministrator or request.user.is_administrator)

class IsModeratorOrAdmin(BasePermission):
    """Allows access only to moderators or administrators."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_moderator or request.user.is_administrator)


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
                "is_active": user.is_active,
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

class FetchEmails(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]  # Only admin can fetch emails

    def get(self, request):
        # No need for additional check since IsAdminOrSuperAdmin handles it
        users = User.objects.all()
        user_emails = [{"email": user.email} for user in users]
        return Response(user_emails, status=200)
    
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    
    @method_decorator(cache_page(300))  # Cache for 5 minutes
    def get(self, request):
        serializer = GetUserSerializer(request.user)
        return Response(serializer.data)

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

class ClientAssignedCommunityManagersView(APIView):
    """
    View to retrieve a list of community managers directly assigned to a specific client.
    """
    permission_classes = [IsAuthenticated] # You might want to add more specific permissions

    def get(self, request, client_id):
        try:
            client = User.objects.get(id=client_id, is_client=True)
        except User.DoesNotExist:
            return Response({"error": "Client not found."}, status=status.HTTP_404_NOT_FOUND)

        assigned_cms = client.assigned_communitymanagerstoclient.all()
        serializer = GetUserSerializer(assigned_cms, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AssignedModeratorCommunityManagersView(APIView):
    """
    View to retrieve a list of community managers assigned by the currently logged-in moderator.
    """
    permission_classes = [IsAuthenticated, IsModeratorOrAdmin]

    def get(self, request):
        moderator = request.user

        # Get all community managers who are in the current moderator's assigned_communitymanagers list.
        assigned_cms = moderator.assigned_communitymanagers.filter(is_community_manager=True)

        cm_data = []
        for cm in assigned_cms:
            cm_data.append({
                "id": cm.id,
                "full_name": cm.full_name,
                "email": cm.email,
                # Add other community manager fields you need
            })

        return Response(cm_data, status=status.HTTP_200_OK)

class AssignedModeratorClientsView(APIView):
    """
    View to retrieve a list of clients directly assigned to the currently logged-in moderator.
    """
    permission_classes = [IsModeratorOrAdmin]

    def get(self, request):
        moderator = request.user  # Get the logged-in moderator.

        # Get all clients where the assigned_moderator is the current moderator.
        clients = User.objects.filter(assigned_moderator=moderator, is_client=True)

        client_data = []
        for client in clients:
            client_data.append({
                "id": client.id,
                "full_name": client.full_name,
                "email": client.email,
                # Add other client fields you need
            })

        return Response(client_data, status=status.HTTP_200_OK)

class EligibleCMsForClient(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def get(self, request, client_id):
        """
        Retrieves a list of community managers eligible for a specific client.

        Eligibility is determined by whether the community managers are directly
        assigned to the moderator who is currently assigned to the client.

        Args:
            request (Request): The incoming HTTP request.
            client_id (int): The ID of the client.

        Returns:
            Response: A JSON response containing a list of community manager data
                      if successful, or an error message if the client has no
                      assigned moderator.
        """
        client = get_object_or_404(User, id=client_id, is_client=True)

        if not client.assigned_moderator:
            return Response({"detail": "This client has no assigned moderator."}, status=status.HTTP_400_BAD_REQUEST)

        moderator = client.assigned_moderator
        # Access the community managers assigned to this moderator using the related_name
        eligible_cms = moderator.assigned_communitymanagers.all()

        serializer = GetUserSerializer(eligible_cms, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    


#create
class CreateUserView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = CreateUserSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                
                
                password = getattr(serializer, 'password', None)
                
                response_data = {"message": "User created successfully"}
                
               
                if settings.DEBUG_EMAIL:
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

class CreateCMView(APIView):
    permission_classes = [IsAuthenticated, IsModerator]  # Only authenticated Moderators can access

    def post(self, request):
        serializer = CreateCMSerializer(data={'email': request.data.get('email')})
        if serializer.is_valid():
            try:
                # Create the Community Manager user
                user = serializer.save()

                # Ensure the request user is a Moderator
                moderator = request.user
                if not moderator.is_moderator:
                    return Response(
                        {"error": "Only moderators can create and assign community managers."},
                        status=status.HTTP_403_FORBIDDEN
                    )

                # Assign the community manager to the moderator
                moderator.assigned_communitymanagers.add(user)
                moderator.save()

                return Response(
                    {"message": f"Community Manager {user.email} created and assigned to you."},
                    status=status.HTTP_201_CREATED
                )

            except Exception as e:
                return Response(
                    {"error": f"Failed to create Community Manager: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#login logout
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

#password
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

class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            serializer.send_reset_email()
            return Response({"message": "Password reset email sent."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"email": "User with this email does not exist."}, status=400)
        except Exception as e:
            # Log the actual error for debugging
            print(f"Password reset error: {str(e)}") 
            return Response(
                {"error": "Failed to send reset email"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, uid, token):
        data = {"uid": uid, "token": token, "new_password": request.data.get("new_password"), "confirm_password": request.data.get("confirm_password")}
        serializer = self.get_serializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Password reset successful."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
#update user


class UpdateUserView(UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = GetUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user_id = self.kwargs.get('user_id')
        obj = get_object_or_404(self.queryset, id=user_id)
        if obj != self.request.user:
            raise PermissionDenied("You can only update your own profile")
        return obj 

    def update(self, request, *args, **kwargs):
        restricted_fields = {
            'is_administrator', 'is_moderator', 'is_community_manager',
            'is_client', 'is_staff', 'is_supplier', 'is_active',
            'is_superuser', 'is_verified'
        }
        
        # Check for restricted fields
        for field in restricted_fields:
            if field in request.data:
                raise PermissionDenied(
                    f"You are not allowed to modify the '{field}' field.",
                    code=status.HTTP_403_FORBIDDEN
                )

        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Store updated fields for the notification
        updated_fields = []
        for field, value in request.data.items():
            if field not in restricted_fields:
                updated_fields.append(field)

        notify_user(
            user=instance,
            title="Profile Updated",
            message="Your profile has been successfully updated.",
            type="profile_update"
        )

        # Use the centralized function to clear user cache
        from apps.accounts.services import clear_user_cache
        clear_user_cache(instance.id)
        
        # For Redis-specific cache clearing with django_redis
        # Invalidate the cache_page decorator cache for CurrentUserView
        try:
            # Get the Redis client from django_redis
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            
            # Clear cache patterns related to the user
            cache_key_pattern = f"*:views.decorators.cache.cache_page.*user*{instance.id}*"
            for key in redis_conn.keys(cache_key_pattern):
                redis_conn.delete(key)
                
            # Also clear the current-user patterns
            current_user_pattern = "*:current-user*"
            for key in redis_conn.keys(current_user_pattern):
                redis_conn.delete(key)
                
        except Exception as e:
            # Log the error but don't interrupt the response
            print(f"Error clearing Redis cache: {str(e)}")

        return Response(serializer.data, status=status.HTTP_200_OK)
    

class AssignCMToClientView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def put(self, request, client_id):
        try:
            client = User.objects.get(id=client_id, is_client=True)
        except User.DoesNotExist:
            return Response({"error": "Client not found."}, status=status.HTTP_404_NOT_FOUND)

        if not client.assigned_moderator:
            return Response({"error": "This client has no assigned moderator. Assign a moderator first."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AssignCMToClientSerializer(data=request.data)
        if serializer.is_valid():
            cm_id = serializer.validated_data["cm_id"]
            try:
                community_manager = User.objects.get(id=cm_id, is_community_manager=True)
            except User.DoesNotExist:
                return Response({"error": "Community Manager not found."}, status=status.HTTP_404_NOT_FOUND)

            # Check if the community manager is assigned to the client's moderator
            if community_manager not in client.assigned_moderator.assigned_communitymanagers.all():
                return Response({"error": "This community manager is not assigned to the client's moderator."}, status=status.HTTP_400_BAD_REQUEST)

            # Assign the community manager to the client
            client.assigned_communitymanagerstoclient.add(community_manager)
            client.save()

            # Notify the community manager about the assignment
            notify_user(
                user=community_manager,
                title="Assigned to Client",
                message=f"You have been assigned to client {client.full_name or client.email}.",
                type="assignment"
            )

            # Notify the client about the assignment
            notify_user(
                user=client,
                title="Community Manager Assigned",
                message=f"Community Manager {community_manager.full_name or community_manager.email} has been assigned to your account.",
                type="community_manager_assignment"
            )

            return Response({"message": f"Community Manager {community_manager.email} assigned to client {client.email}."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RemoveCommunityManagerFromModeratorView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def delete(self, request, moderator_id, cm_id):
        try:
            moderator = User.objects.get(id=moderator_id, is_moderator=True)
            cm_to_remove = User.objects.get(id=cm_id, is_community_manager=True)

            if cm_to_remove in moderator.assigned_communitymanagers.all():
                moderator.assigned_communitymanagers.remove(cm_to_remove)

                # Now, unassign this CM from all clients associated with this moderator
                clients_with_this_moderator = User.objects.filter(
                    is_client=True, assigned_moderator=moderator
                )
                for client in clients_with_this_moderator:
                    if cm_to_remove in client.assigned_communitymanagerstoclient.all():
                        client.assigned_communitymanagerstoclient.remove(cm_to_remove)
                        client.save()  # Important to save the client object

                        # Notify the client about the removal
                        notify_user(
                            user=client,
                            title="Community Manager Removed",
                            message=f"Community Manager {cm_to_remove.full_name or cm_to_remove.email} has been removed from your account.",
                            type="removal"
                        )

                # Notify the community manager about the removal
                notify_user(
                    user=cm_to_remove,
                    title="Unassigned from Moderator",
                    message=f"You have been unassigned from Moderator {moderator.full_name or moderator.email}.",
                    type="removal"
                )

                # Notify the moderator about the removal
                notify_user(
                    user=moderator,
                    title="Community Manager Removed",
                    message=f"Community Manager {cm_to_remove.full_name or cm_to_remove.email} has been removed from your assignments.",
                    type="removal"
                )

                return Response({"message": "Community Manager unassigned from Moderator and associated clients."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "This Community Manager is not assigned to this Moderator."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
class RemoveModeratorFromClientView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def delete(self, request, client_id):
        try:
            client = User.objects.get(id=client_id, is_client=True)

            if client.assigned_moderator is None:
                return Response({"message": "No moderator assigned to this client."}, status=status.HTTP_400_BAD_REQUEST)

            # Unassign the moderator
            moderator = client.assigned_moderator
            client.assigned_moderator = None

            # Unassign all community managers associated with this client
            client.assigned_communitymanagerstoclient.clear()

            client.save()

            # Notify the moderator about the removal
            notify_user(
                user=moderator,
                title="Unassigned from Client",
                message=f"You have been unassigned from client {client.full_name or client.email}.",
                type="removal"
            )

            # Notify the client about the removal
            notify_user(
                user=client,
                title="Moderator Removed",
                message="Your assigned moderator has been removed.",
                type="removal"
            )

            return Response({"message": "Moderator unassigned from client and associated community manager assignments removed."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "Client not found."}, status=status.HTTP_404_NOT_FOUND)

class RemoveClientCommunityManagersView(generics.UpdateAPIView):
    serializer_class = RemoveCMsFromClientSerializer
    permission_classes = [IsModeratorOrAdmin]
    lookup_url_kwarg = 'client_id'
    queryset = User.objects.filter(is_client=True)

    def update(self, request, *args, **kwargs):
        client = self.get_object()  # Get the client object
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cm_ids_to_remove = serializer.validated_data['community_manager_ids']

        # Get the currently assigned community managers for the client
        assigned_cms_to_client = client.assigned_communitymanagerstoclient.all()

        # Filter for the community managers that are currently assigned to the client AND in the list to remove
        cms_to_remove = assigned_cms_to_client.filter(id__in=cm_ids_to_remove)

        # Check if all provided IDs are valid and assigned to the client
        invalid_ids = set(cm_ids_to_remove) - set(cms_to_remove.values_list('id', flat=True))
        if invalid_ids:
            return Response(
                {"error": f"The following community manager IDs are not currently assigned to this client: {list(invalid_ids)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Remove the specified community managers from the client's assignment
        client.assigned_communitymanagerstoclient.remove(*cms_to_remove)
        client.save()

        # Return the updated client data
        client_serializer = GetUserSerializer(client)
        return Response(client_serializer.data, status=status.HTTP_200_OK)

        
    

class ListUsers(APIView):
    permission_classes = [IsAdminOrSuperAdmin]  # Only authenticated users can access this view
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
    permission_classes = [IsAdminOrSuperAdmin]  # <-- Everyone can access this view

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

            # Notify the moderator
            notify_user(
                user=moderator,
                title="Assigned as Moderator",
                message=f"You have been assigned as a moderator for client {client.full_name or client.email}.",
                type="assignment"
            )

            # Notify the client
            notify_user(
                user=client,
                title="Moderator Assigned",
                message=f"Moderator {moderator.full_name or moderator.email} has been assigned to your account.",
                type="assignment"
            )

            # Send email asynchronously using Celery
            send_celery_email.delay(
                'You have been assigned as a moderator',
                f'Hello {moderator.full_name or moderator.email},\n\nYou have been assigned as a moderator for client {client.full_name or client.email}. Please review the client details and take the necessary actions.\n\nBest regards,\nAdmin',
                moderator.email
            )

            return Response({"message": f"Moderator {moderator.email} assigned to client {client.email}."})

        return Response(serializer.errors, status=400)

class AssignCommunityManagerToModeratorView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]  

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

            # Notify the community manager
            notify_user(
                user=cm,
                title="Assigned to Moderator",
                message=f"You have been assigned to Moderator {moderator.full_name or moderator.email}.",
                type="assignment"
            )

            # Notify the moderator
            notify_user(
                user=moderator,
                title="Community Manager Assigned",
                message=f"Community Manager {cm.full_name or cm.email} has been assigned to you.",
                type="assignment"
            )

            # Send email asynchronously using Celery
            send_celery_email.delay(
                'You have been assigned to a moderator',
                f'Hello {cm.full_name or cm.email},\n\nYou have been assigned to Moderator {moderator.full_name or moderator.email}. Please review and collaborate.\n\nBest regards,\nAdmin',
                cm.email
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

                # Notify the community manager about the removal
                notify_user(
                    user=cm,
                    title="Unassigned from Moderator",
                    message=f"You have been unassigned from Moderator {moderator.full_name or moderator.email}.",
                    type="removal"
                )

                # Notify the moderator about the removal
                notify_user(
                    user=moderator,
                    title="Community Manager Removed",
                    message=f"Community Manager {cm.full_name or cm.email} has been removed from your assignments.",
                    type="removal"
                )

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
           
            moderator = client.assigned_moderator
            client.assigned_moderator = None
            client.save()

            # Notify the moderator about the removal
            notify_user(
                user=moderator,
                title="Unassigned from Client",
                message=f"You have been unassigned from client {client.full_name or client.email}.",
                type="removal"
            )

            # Notify the client about the removal
            notify_user(
                user=client,
                title="Moderator Removed",
                message=f"Your assigned moderator {moderator.full_name or moderator.email} has been removed.",
                type="removal"
            )
            return Response({"message": "Moderator unassigned from client."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "Client not found."}, status=status.HTTP_404_NOT_FOUND)

    
class AdminDeleteUserView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]  # Only administrators or superadministrators can access this view

    def delete(self, request, user_id):
        try:
            user_to_delete = User.objects.get(pk=user_id)

            # Prevent administrators and superadministrators from deleting themselves
            if user_to_delete == request.user:
                return Response(
                    {"error": "You cannot delete yourself."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Check if the user to be deleted is an administrator
            if user_to_delete.is_administrator:
                # Only the superadministrator can delete other administrators
                if not request.user.is_superadministrator:
                    return Response(
                        {"error": "Only the superadministrator can delete other administrators."},
                        status=status.HTTP_403_FORBIDDEN
                    )

            # Proceed with deletion
            email = user_to_delete.email  # Store email before deletion for the response message
            user_to_delete.delete()
            return Response(
                {'message': f'User with ID {user_id} (email: {email}) has been deleted successfully'},
                status=status.HTTP_200_OK
            )

        except User.DoesNotExist:
            return Response({"error": "User does not exist"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"Error deleting user: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user_data = get_cached_user_data(request.user)  # Use cached data
        return Response(user_data)

class GetUserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id=None):
        # If no user_id provided, return the current user's profile
        if not user_id:
            user_id = request.user.id
            
        # Try to get user data from cache
        cache_key = f"user_profile:{user_id}"
        cached_profile = cache.get(cache_key)
        
        if cached_profile is not None:
            return Response(cached_profile)
            
        # If not in cache, get from database
        try:
            user = User.objects.get(id=user_id)
            serializer = GetUserSerializer(user)
            profile_data = serializer.data
            
            # Cache the profile data
            cache.set(cache_key, profile_data, 3600)  # Cache for 1 hour
            
            return Response(profile_data)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

class GetUserStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        user_id = user.id
        
        # Try to get user stats from cache
        cache_key = f"user_stats:{user_id}"
        cached_stats = cache.get(cache_key)
        
        if cached_stats is not None:
            return Response(cached_stats)
        
        # If not in cache, compute and cache
        from apps.notifications.models import Notification
        from apps.content.models import Content
        
        stats = {
            'unread_notifications': Notification.objects.filter(
                recipient=user, 
                is_read=False
            ).count(),
            
            'total_content': Content.objects.filter(
                author=user
            ).count(),
            
            # Add any other stats you want to track
        }
        
        # Cache the stats
        cache.set(cache_key, stats, 1800)  # Cache for 30 minutes
        
        return Response(stats)


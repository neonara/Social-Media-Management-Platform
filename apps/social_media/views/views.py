from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, PermissionDenied
from apps.social_media.models import SocialPage
from apps.accounts.models import User
from permissions.permissions import IsModeratorOrCM, IsClient

from apps.social_media.serializers import SocialPageSerializer

class SocialPagesView(APIView):
    """
    Get all social media pages connected to the current user (client)
    """
    permission_classes = [IsAuthenticated, IsClient]
    
    def get(self, request):
        pages = SocialPage.objects.filter(client=request.user)
        serializer = SocialPageSerializer(pages, many=True)
        
        # Create a structured response with details for each platform
        response = {
            'pages': serializer.data,
            'connected_platforms': {
                'facebook': any(page['platform'] == 'facebook' for page in serializer.data),
                'instagram': any(page['platform'] == 'instagram' for page in serializer.data),
                'linkedin': any(page['platform'] == 'linkedin' for page in serializer.data)
            }
        }
        
        return Response(response)
        
class ClientSocialPagesView(APIView):
    """
    Get all social media pages connected to a specific client (for moderators and community managers)
    """
    permission_classes = [IsAuthenticated, IsModeratorOrCM]
    
    def get(self, request, client_id):
        # client_id is now received directly from URL path parameter
        try:
            client = User.objects.get(id=client_id, is_client=True)
        except User.DoesNotExist:
            raise NotFound("Client not found")
        
        pages = SocialPage.objects.filter(client=client)
        serializer = SocialPageSerializer(pages, many=True)
        
        # Create a structured response with details for each platform
        # response = {
        #     'client_id': client.id,
        #     'client_name': f"{client.first_name} {client.last_name}",
        #     'pages': serializer.data,
        #     'connected_platforms': {
        #         'facebook': any(page['platform'] == 'facebook' for page in serializer.data),
        #         'instagram': any(page['platform'] == 'instagram' for page in serializer.data),
        #         'linkedin': any(page['platform'] == 'linkedin' for page in serializer.data)
        #     }
        # }
        response = serializer.data
        if not response:
            raise NotFound("No social pages found for this client")
        
        return Response(response)

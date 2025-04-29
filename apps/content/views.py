from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework import generics
from .models import Post, Media
from django.db import models
from .serializers import PostSerializer, MediaSerializer
from django.contrib.auth.models import User

class IsModerator(BasePermission):
    """Allows access only to administrators."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_moderator
    
class IsModeratorOrCM(BasePermission):
    """Allows access only to moderators or administrators."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_moderator or request.user.is_community_manager)


class CreatePostView(APIView):
    permission_classes = [IsAuthenticated, IsModeratorOrCM]

    def post(self, request, client_id=None):
        data = request.data.copy()
        data['status'] = request.data.get('status', 'scheduled')
        
        # Handle client assignment from URL or request data
        if client_id:
            try:
                client = User.objects.get(
                    id=client_id,
                    is_client=True,
                    assigned_moderator=request.user
                )
                data['client'] = client.id
            except User.DoesNotExist:
                return Response(
                    {"error": "Invalid client or client not assigned to you"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif data.get('client'):
            # Alternative: client ID comes from request data
            try:
                client = User.objects.get(
                    id=data['client'],
                    is_client=True,
                    assigned_moderator=request.user
                )
            except User.DoesNotExist:
                return Response(
                    {"error": "Invalid client or client not assigned to you"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Rest of your existing create logic...
        if not data.get('media_files') and request.FILES:
            data['media_files'] = request.FILES.getlist('media_files')

        serializer = PostSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            post = serializer.save(
                creator=request.user,
                status=data['status']
            )
            return Response(PostSerializer(post, context={'request': request}).data, 
                          status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ListPostsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_moderator:
            # Get posts created by the moderator AND posts for their clients
            posts = Post.objects.filter(
                models.Q(creator=request.user) | 
                models.Q(client__assigned_moderator=request.user)
            )
        else:
            # For regular users, just show their own posts
            posts = Post.objects.filter(creator=request.user)
            
        serializer = PostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class UpdatePostView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        """Retrieve post details with properly formatted media URLs"""
        try:
            # Ensure the post exists and is created by the logged-in user
            post = Post.objects.get(id=post_id, creator=request.user)
            serializer = PostSerializer(post, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({"error": "Post not found or you do not have permission to access it."}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, post_id):
        """Update post with handling for both existing and new media"""
        try:
            # Ensure the post exists and is created by the logged-in user
            post = Post.objects.get(id=post_id, creator=request.user)
        except Post.DoesNotExist:
            return Response({"error": "Post not found or you do not have permission to update it."}, status=status.HTTP_404_NOT_FOUND)

        # Prepare data with proper file handling
        data = request.data.copy()
        media_files = request.FILES.getlist('media_files', [])

        # Handle media removal if needed
        media_to_remove = data.pop('media_to_remove', [])
        if media_to_remove:
            post.media.remove(*media_to_remove)

        serializer = PostSerializer(
            post,
            data=data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            # Save the post first
            post = serializer.save()

            # Process new media files
            if media_files:
                self._handle_media_upload(post, media_files, request.user)

            # Return updated post data with proper media URLs
            updated_serializer = PostSerializer(post, context={'request': request})
            return Response(updated_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _handle_media_upload(self, post, media_files, user):
        """Helper method to handle media uploads"""
        for file in media_files:
            media_instance = Media.objects.create(
                file=file,
                name=file.name,
                creator=user,
                type=self._determine_file_type(file.name)
            )
            post.media.add(media_instance)

    def _determine_file_type(self, filename):
        """Determine media type based on file extension"""
        filename = filename.lower()
        if filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            return 'image'
        elif filename.endswith(('.mp4', '.avi', '.mov', '.webm')):
            return 'video'
        elif filename.endswith(('.pdf', '.doc', '.docx', '.txt')):
            return 'document'
        return 'other'


#media

class MediaListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MediaSerializer

    def get_queryset(self):
        return Media.objects.filter(creator=self.request.user)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

class MediaDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MediaSerializer

    def get_queryset(self):
        return Media.objects.filter(creator=self.request.user)

#drafts
class FetchDraftsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Explicitly filter by both status AND creator
        drafts = Post.objects.filter(
            creator=request.user,  # This is the critical filter
            status='draft'
        ).prefetch_related('media')

        serializer = PostSerializer(drafts, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class SaveDraftView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        data['status'] = 'draft'  # Explicitly set status to 'draft'
        serializer = PostSerializer(data=data, context={'request': request})

        if serializer.is_valid():
            post = serializer.save(creator=request.user)
            return Response(PostSerializer(post, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeletePostView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, post_id):
        try:
            # Fetch the post created by the logged-in user
            post = Post.objects.get(id=post_id, creator=request.user)
            post.delete()
            return Response({"message": "Post deleted successfully."}, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({"error": "Post not found."}, status=status.HTTP_404_NOT_FOUND)
        
class ClientPostsView(APIView):
    permission_classes = [IsAuthenticated, IsModerator]

    def get(self, request, client_id):
        # Verify the client is assigned to this moderator
        try:
            client = User.objects.get(
                id=client_id,
                is_client=True,
                assigned_moderator=request.user
            )
        except User.DoesNotExist:
            return Response(
                {"error": "Client not found or not assigned to you"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get posts for this client
        posts = Post.objects.filter(client=client)
        serializer = PostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)
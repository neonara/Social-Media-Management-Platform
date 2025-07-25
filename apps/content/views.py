from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework import generics
from django.core.cache import cache
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

from apps.accounts.tasks import send_celery_email
from apps.notifications.services import notify_user

from .models import Post, Media
from .serializers import PostSerializer, MediaSerializer
from apps.accounts.models import User

from django.contrib.auth import get_user_model
User = get_user_model() 

class IsCM(BasePermission):
    """Allows access only to administrators."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_community_manager


class IsModerator(BasePermission):
    """Allows access only to administrators."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_moderator
    
class IsModeratorOrCM(BasePermission):
    """Allows access only to moderators or administrators."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_moderator or request.user.is_community_manager)

class IsAssignedToPost(BasePermission):
    """
    Custom permission to allow only assigned users to edit a post.
    """

    def has_object_permission(self, request, view, obj):
        # Ensure the object is a Post and the user is assigned to it
        return obj.is_user_assigned(request.user)

# Cache Helpers
def cache_key(model_name, pk=None):
    prefix = f"cache:{model_name.lower()}"  
    return f"{prefix}:{pk}" if pk else f"{prefix}:all"

def get_cached_or_query(model, pk=None):
    key = f"model_{model.__name__.lower()}_{pk if pk else 'all'}"
    data = cache.get(key)
    
    if data is None:
        data = model.objects.get(pk=pk) if pk else model.objects.all()
        cache.set(key, data)
    return data

def invalidate_cache(model, pk=None):
    keys = [
        f"model_{model.__name__.lower()}_{pk if pk else 'all'}",
        f"user_posts_*",  # Will need manual handling for pattern deletion
    ]
    for key in keys:
        cache.delete(key)

#view classes     
class CreatePostView(APIView):
    permission_classes = [IsAuthenticated, IsModeratorOrCM]

    def post(self, request, client_id=None):
        data = request.data.copy()
        files = request.FILES
        print("Raw request data:", request.data)
        print("Content-Type:", request.content_type)
        
        # Debug headers
        print("Request headers:", {k: v for k, v in request.META.items() if k.startswith('HTTP_')})

        # Client Validation - Look for 'client_id' or 'client' in the request data
        client_id = data.get('client_id') or data.get('client', client_id)
        print(f"Extracted client_id: {client_id}")
        
        if not client_id:
            return Response(
                {"error": "Client ID is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            client = get_cached_or_query(User, client_id)
            if not client.is_client:
                raise User.DoesNotExist
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid client ID."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Permission Check
        if request.user.is_community_manager:
            if not client.assigned_communitymanagerstoclient.filter(id=request.user.id).exists():
                return Response(
                    {"error": "Not assigned to this client."},
                    status=status.HTTP_403_FORBIDDEN
                )
        elif request.user.is_moderator:
            if client.assigned_moderator != request.user:
                return Response(
                    {"error": "Not assigned to this client."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Media Processing - Using the old approach
        if not data.get('media_files') and files:
            if 'media_files' in files:
                # Multiple files with same field name
                data['media_files'] = files.getlist('media_files')
            else:
                # Process indexed files (media_files[0], media_files[1], etc.)
                media_files_list = []
                media_keys = [key for key in files if key.startswith('media_files[')]
                media_keys.sort(key=lambda x: int(x.split('[')[1].split(']')[0]))
                
                for key in media_keys:
                    file = files.get(key)
                    self.validate_file(file)
                    media_files_list.append(file)
                    
                data['media_files'] = media_files_list

        # Post Creation
        data['client'] = client.id
        # Set status to 'pending' for client approval, unless it's a draft
        if data.get('status') != 'draft':
            data['status'] = 'pending'
                
        serializer = PostSerializer(data=data, context={'request': request})
        
        if serializer.is_valid():
            try:
                post = serializer.save(creator=request.user, client=client)
                scheduled_for = post.scheduled_for  # This should now be a datetime object

                # Notify the client about the post creation for review
                if post.status == 'pending':
                    notify_user(
                        user=client,
                        title="Post Pending Your Approval",
                        message=f"A post '{post.title}' has been created and is pending your approval. Please review and approve or reject it.",
                        type="post_pending_approval"
                    )
                    print(f"Approval notification sent to {client}")

                    # Send email asynchronously using Celery for approval
                    send_celery_email.delay(
                        'Post Pending Your Approval',
                        f'Hello {client.full_name or client.email}, A post titled "{post.title}" has been created and is pending your approval. Please log in to review and approve or reject this post. Scheduled for: {scheduled_for}',
                        [client.email],
                        fail_silently=False
                    )
                else:
                    # Original notification for drafts or other statuses
                    notify_user(
                        user=client,
                        title="Post is created",
                        message=f"A post has been created in your pages and scheduled for {scheduled_for}",
                        type="content"
                    )
                    print(f"Notification sent to {client}")

                    # Send email asynchronously using Celery
                    send_celery_email.delay(
                        'Post is created',
                        f'Hello {client.full_name or client.email}, A post has been created in your pages and scheduled for {scheduled_for}',
                        [client.email],
                        fail_silently=False
                    )

                # Cache the newly created post
                post_data = PostSerializer(post, context={'request': request}).data
                cache.set(f"post:{post.id}", post_data, timeout=60*60)  # Cache for 1 hour
                cache.set(f"post_detail:{post.id}", post_data, timeout=60*60)
                
                # Invalidate list caches
                invalidate_cache(Post)
                cache.delete(f"user_posts:{request.user.id}")
                
                return Response(post_data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def validate_file(self, file):
        max_size = 100 * 1024 * 1024
        if file.size > max_size:
            raise ValidationError(f"File too large: {file.name} ({file.size/1024/1024:.1f}MB)")
        
        allowed_types = [
            'image/jpeg', 
            'image/jpg', 
            'image/png', 
            'video/mp4', 
            'video/quicktime'
        ]
        if file.content_type not in allowed_types:
            raise ValidationError(f"Unsupported file type: {file.content_type}")

    def get_file_type(self, content_type):
        return 'video' if 'video' in content_type else 'image'
    
class GetPostCreatorsView(APIView):
    """
    View to fetch all unique creators of posts.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Fetch all posts
        posts = Post.objects.all()

        # Get the creators of these posts
        creators = User.objects.filter(
            id__in=posts.values_list('creator_id', flat=True)
        ).distinct()

        # Serialize the creators
        creator_data = [
            {
                "id": creator.id,
                "full_name": creator.full_name,
                "email": creator.email,
            }
            for creator in creators
        ]

        return Response(creator_data, status=status.HTTP_200_OK)

class UpdatePostToDraftView(APIView):
    """
    View to update a scheduled post's status to 'draft'.
    """
    permission_classes = [IsAuthenticated, IsAssignedToPost]

    def patch(self, request, post_id):
        try:
            # Fetch the post
            post = Post.objects.get(id=post_id, status='scheduled')
            self.check_object_permissions(request, post)

            # Update the post's status to 'draft'
            post.status = 'draft'
            post.save()

            # Invalidate related caches
            cache.delete(f"post:{post_id}")
            cache.delete(f"post_detail:{post_id}")
            cache.delete(f"user_posts:{request.user.id}")
            cache.delete(f"user_drafts:{request.user.id}")  # <-- Add this line
            invalidate_cache(Post, post_id)

            # Serialize the updated post
            updated_data = PostSerializer(post, context={'request': request}).data
            
            return Response(updated_data, status=status.HTTP_200_OK)

        except Post.DoesNotExist:
            return Response(
                {"error": "Scheduled post not found or you don't have permission."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ListPostsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cache_key = f"user_posts:{request.user.id}"
        cached_data = cache.get(cache_key)

        if cached_data is None:
            # Fetch posts with related client and creator objects
            posts = Post.objects.filter(
                models.Q(creator=request.user) |
                models.Q(client=request.user) |
                models.Q(creator__assigned_moderator=request.user) |
                models.Q(creator__assigned_communitymanagers=request.user)
            ).distinct().select_related('client', 'creator').prefetch_related('media')

            # Serialize the posts with context
            serializer = PostSerializer(posts, many=True, context={'request': request})
            cached_data = serializer.data

            # Cache the serialized data
            cache.set(cache_key, cached_data, timeout=60 * 10)  
        return Response(cached_data, status=status.HTTP_200_OK)

class UpdatePostView(APIView):
    permission_classes = [IsAuthenticated, IsAssignedToPost]
    
    def get(self, request, post_id):  
        try:
            post = Post.objects.get(id=post_id)
            self.check_object_permissions(request, post)
            serializer = PostSerializer(post, context={'request': request})
            return Response(serializer.data)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)


    def patch(self, request, post_id):
        try:
            # First try to get the post
            post = Post.objects.get(id=post_id)
            self.check_object_permissions(request, post)

            # Rest of your update logic...
            data = request.data.copy()
            media_files = request.FILES.getlist('media_files', [])

            # Handle client update
            client_id = data.get('client')
            if client_id:
                try:
                    client = User.objects.get(id=client_id, is_client=True)
                    post.client = client
                except User.DoesNotExist:
                    return Response({"error": "Invalid client ID."}, 
                                  status=status.HTTP_400_BAD_REQUEST)

            serializer = PostSerializer(
                post,
                data=data,
                partial=True,
                context={'request': request}
            )

            if serializer.is_valid():
                post = serializer.save(last_edited_by=request.user)

                
                if media_files:
                    self._handle_media_upload(post, media_files, request.user)

                
                updated_data = PostSerializer(post, context={'request': request}).data
                cache.set(f"post:{post_id}", updated_data, timeout=60*60)
                cache.set(f"post_detail:{post_id}", updated_data, timeout=60*60)
                cache.delete(f"user_posts:{request.user.id}")
                cache.delete(f"user_drafts:{request.user.id}")
                invalidate_cache(Post)

                return Response(updated_data, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Post.DoesNotExist:
            return Response(
                {"error": f"Post with ID {post_id} not found or you don't have permission"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
   
    def _handle_media_upload(self, post, media_files, user):
        for file in media_files:
            media_instance = Media.objects.create(
                file=file,
                name=file.name,
                creator=user,
                type=self._determine_file_type(file.name)
            )
            post.media.add(media_instance)

    def _determine_file_type(self, filename):
        filename = filename.lower()
        if filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            return 'image'
        elif filename.endswith(('.mp4', '.avi', '.mov', '.webm')):
            return 'video'
        return 'other'

class FetchCMClientPostsView(APIView):
    permission_classes = [IsAuthenticated, IsCM]

    def get(self, request):
        user = request.user
        cache_key = f"cm_posts:{user.id}"
        cached_data = cache.get(cache_key)
        
        if cached_data is None:
            assigned_clients = User.objects.filter(
                is_client=True,
                assigned_communitymanagerstoclient=user
            )
            
            creator_ids = [user.id]
            if user.assigned_moderator:
                creator_ids.append(user.assigned_moderator.id)
                creator_ids.extend(
                    user.assigned_moderator.assigned_communitymanagers
                    .exclude(id=user.id)
                    .values_list('id', flat=True)
                )
            
            posts = Post.objects.filter(
                client__in=assigned_clients,
                creator_id__in=creator_ids
            ).select_related('client', 'creator').prefetch_related('media')
            
            serializer = PostSerializer(posts, many=True, context={'request': request})
            cached_data = serializer.data
            cache.set(cache_key, cached_data, timeout=60*10)  # 10 minutes
        
        return Response(cached_data, status=status.HTTP_200_OK)

class MediaListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MediaSerializer

    def get_queryset(self):
        return Media.objects.filter(creator=self.request.user)

    def perform_create(self, serializer):
        instance = serializer.save(creator=self.request.user)
        invalidate_cache(Media)

class MediaDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MediaSerializer

    def get_queryset(self):
        return Media.objects.filter(creator=self.request.user)

    def perform_destroy(self, instance):
        instance.delete()
        invalidate_cache(Media, instance.id)

class FetchDraftsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Cache key for user drafts
        cache_key = f"user_drafts:{request.user.id}"
        cached_data = cache.get(cache_key)

        if cached_data is None:
            # Fetch drafts where the creator is the logged-in user
            drafts = Post.objects.filter(
                creator=request.user,
                status='draft'
            ).distinct()

            # Serialize the drafts
            serializer = PostSerializer(drafts, many=True, context={'request': request})
            cached_data = serializer.data

            # Cache the serialized drafts for 5 minutes
            cache.set(cache_key, cached_data, timeout=60 * 5)

        return Response(cached_data, status=status.HTTP_200_OK)

class SaveDraftView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        data['status'] = 'draft'
        serializer = PostSerializer(data=data, context={'request': request})

        if serializer.is_valid():
            post = serializer.save(creator=request.user)
            cache.delete(f"user_drafts:{request.user.id}")
            invalidate_cache(Post)
            return Response(
                PostSerializer(post, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeletePostView(APIView):
    permission_classes = [IsAuthenticated, IsModeratorOrCM]

    def delete(self, request, post_id):
        """
        Delete a post if the user is assigned to it.
        """
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response(
                {"error": "Post not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if the user is assigned to the post
        if not post.is_user_assigned(request.user):
            return Response(
                {"error": "You are not authorized to delete this post."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Cache invalidation
        invalidate_cache(Post)
        invalidate_cache(Post, post_id)
        
        post.delete()
        
        return Response(
            {"message": "Post deleted successfully."}, 
            status=status.HTTP_204_NO_CONTENT
        )


class ApprovePostView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, post_id):
        """
        Approve a post by changing its status to 'scheduled'.
        Clients can approve their own posts, moderators can approve any post.
        """
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response(
                {"error": "Post not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions - client can approve their own posts, moderators can approve any
        if not (request.user.is_moderator or post.client == request.user):
            return Response(
                {"error": "You are not authorized to approve this post."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if post is in pending status
        if post.status != 'pending':
            return Response(
                {"error": "Only pending posts can be approved."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get feedback from request (optional for approval)
        feedback = request.data.get('feedback', '')
        
        # Update post status to scheduled
        post.status = 'scheduled'
        post.last_edited_by = request.user
        if feedback:
            post.feedback = feedback
            post.feedback_by = request.user
            post.feedback_at = timezone.now()
        post.save()
        
        # Cache invalidation
        invalidate_cache(Post)
        invalidate_cache(Post, post_id)
        
        # Notify the creator about approval
        if post.creator and post.creator != request.user:
            approval_message = f"Your post '{post.title}' has been approved and scheduled."
            if feedback:
                approval_message += f" Feedback: {feedback}"
            notify_user(
                user=post.creator,
                message=approval_message,
                type="post_approved"
            )
        
        # Notify the client about approval (if approved by moderator)
        if post.client and post.client != request.user and request.user.is_moderator:
            approval_message = f"The post '{post.title}' has been approved and scheduled."
            if feedback:
                approval_message += f" Feedback: {feedback}"
            notify_user(
                user=post.client,
                message=approval_message,
                type="post_approved"
            )
        
        # Notify moderator if client approved the post
        if request.user == post.client and post.creator and post.creator.is_moderator:
            approval_message = f"The post '{post.title}' has been approved by the client and is now scheduled."
            if feedback:
                approval_message += f" Client feedback: {feedback}"
            notify_user(
                user=post.creator,
                message=approval_message,
                type="post_approved"
            )
        
        response_data = {
            "message": "Post approved successfully.",
            "post": PostSerializer(post).data
        }
        if feedback:
            response_data["feedback"] = feedback
        
        return Response(response_data, status=status.HTTP_200_OK)


class RejectPostView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, post_id):
        """
        Reject a post by changing its status to 'rejected'.
        Clients can reject their own posts, moderators can reject any post.
        """
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response(
                {"error": "Post not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions - client can reject their own posts, moderators can reject any
        if not (request.user.is_moderator or post.client == request.user):
            return Response(
                {"error": "You are not authorized to reject this post."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if post is in pending status
        if post.status != 'pending':
            return Response(
                {"error": "Only pending posts can be rejected."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get feedback from request
        feedback = request.data.get('feedback', 'No feedback provided')
        
        # Update post status to rejected
        post.status = 'rejected'
        post.last_edited_by = request.user
        post.feedback = feedback
        post.feedback_by = request.user
        post.feedback_at = timezone.now()
        post.save()
        
        # Cache invalidation
        invalidate_cache(Post)
        invalidate_cache(Post, post_id)
        
        # Notify the creator about rejection
        if post.creator and post.creator != request.user:
            notify_user(
                title=f"Post '{post.title}' Rejected",
                user=post.creator,
                message=f"Your post '{post.title}' has been rejected. Feedback: {feedback}",
                type="post_rejected"
            )
        
        # Notify the client about rejection (if rejected by moderator)
        if post.client and post.client != request.user and request.user.is_moderator:
            notify_user(
                title=f"Post '{post.title}' Rejected",
                user=post.client,
                message=f"The post '{post.title}' has been rejected. Feedback: {feedback}",
                type="post_rejected"
            )
        
        # Notify moderator if client rejected the post
        if request.user == post.client and post.creator and post.creator.is_moderator:
            notify_user(
                title=f"Post '{post.title}' Rejected",
                user=post.creator,
                message=f"The post '{post.title}' has been rejected by the client. Feedback: {feedback}",
                type="post_rejected"
            )
        
        return Response(
            {
                "message": "Post rejected successfully.",
                "post": PostSerializer(post).data,
                "feedback": feedback
            }, 
            status=status.HTTP_200_OK
        )

class FetchPendingPostsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Fetch pending posts for the authenticated user.
        - Clients see their own pending posts
        - Moderators see all pending posts
        - CMs see pending posts for their assigned clients
        """
        cache_key = f"pending_posts:{request.user.id}"
        cached_data = cache.get(cache_key)

        if cached_data is None:
            if request.user.is_client:
                # Clients see their own pending posts
                pending_posts = Post.objects.filter(
                    client=request.user,
                    status='pending'
                ).select_related('creator', 'client').prefetch_related('media')
            
            elif request.user.is_moderator:
                # Moderators see all pending posts
                pending_posts = Post.objects.filter(
                    status='pending'
                ).select_related('creator', 'client').prefetch_related('media')
            
            elif request.user.is_community_manager:
                # CMs see pending posts for their assigned clients
                assigned_clients = User.objects.filter(
                    is_client=True,
                    assigned_communitymanagerstoclient=request.user
                )
                pending_posts = Post.objects.filter(
                    client__in=assigned_clients,
                    status='pending'
                ).select_related('creator', 'client').prefetch_related('media')
            
            else:
                pending_posts = Post.objects.none()

            # Serialize the pending posts
            serializer = PostSerializer(pending_posts, many=True, context={'request': request})
            cached_data = serializer.data

            # Cache the serialized data for 5 minutes
            cache.set(cache_key, cached_data, timeout=60 * 5)

        return Response(cached_data, status=status.HTTP_200_OK)

class PostFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        """
        Get feedback for a specific post.
        Only accessible to users who have access to the post.
        """
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response(
                {"error": "Post not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user has access to this post
        if not (post.client == request.user or 
                post.creator == request.user or 
                request.user.is_moderator or
                (request.user.is_community_manager and 
                 post.client and post.client.assigned_communitymanagerstoclient.filter(id=request.user.id).exists())):
            return Response(
                {"error": "You are not authorized to view feedback for this post."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        feedback_data = {
            "post_id": post.id,
            "post_title": post.title,
            "current_status": post.status,
            "has_feedback": post.has_feedback(),
            "feedback": post.feedback,
            "feedback_by": {
                "id": post.feedback_by.id,
                "name": post.feedback_by.full_name or post.feedback_by.email,
                "email": post.feedback_by.email
            } if post.feedback_by else None,
            "feedback_at": post.feedback_at
        }
        
        return Response(feedback_data, status=status.HTTP_200_OK)





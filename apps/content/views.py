from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from django.core.cache import cache
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.tasks import send_celery_email
from apps.notifications.services import notify_user
from permissions.permissions import (
    IsCommunityManager,
    IsModeratorOrCMOrAdmin,
    IsAssignedToPostOrAdmin
)

from .models import Post, Media
from .serializers import PostSerializer, MediaSerializer
from apps.accounts.models import User


# Cache Helpers
def cache_key(model_name, pk=None):
    prefix = f"cache:{model_name.lower()}"  
    return f"{prefix}:{pk}" if pk else f"{prefix}:all"

def get_cached_or_query(model, pk=None):
    # TEMPORARY: Override caching until cache issues are resolved
    # Always query directly from database
    return model.objects.get(pk=pk) if pk else model.objects.all()
    
    # Original cached implementation (disabled temporarily):
    # key = f"model_{model.__name__.lower()}_{pk if pk else 'all'}"
    # data = cache.get(key)
    # 
    # if data is None:
    #     data = model.objects.get(pk=pk) if pk else model.objects.all()
    #     cache.set(key, data)
    # return data

def invalidate_cache(model, pk=None):
    """Clear post-related cached data using Redis pattern deletion"""
    from django.core.cache import cache
    from django_redis import get_redis_connection
    
    try:
        # Get Redis connection
        redis_conn = get_redis_connection("default")
        
        # Clear all user-specific post caches for all users
        patterns = [
            "user_posts:*",
            "cm_posts:*", 
            "pending_posts:*",
            "scheduled_posts_*",
            "draft_posts_*",
        ]
        
        for pattern in patterns:
            keys = redis_conn.keys(pattern)
            if keys:
                redis_conn.delete(*keys)
        
        # Clear general post cache
        cache.delete('all_posts')
        cache.delete('dashboard_posts')
        
        # Clear specific model caches
        if pk:
            cache.delete(f"model_{model.__name__.lower()}_{pk}")
            cache.delete(f"post:{pk}")
            cache.delete(f"post_detail:{pk}")
        else:
            cache.delete(f"model_{model.__name__.lower()}_all")
            
        print(f"Cache invalidated for {model.__name__} (pk={pk})")
            
    except Exception as e:
        print(f"Error invalidating cache: {e}")
        # Fallback to Django cache if Redis connection fails
        cache.clear()

#view classes     
class CreatePostView(APIView):
    permission_classes = [IsAuthenticated, IsModeratorOrCMOrAdmin]

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
        # Administrators can create posts for any client (no additional check needed)

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

                # Notify the client about the post creation for review (avoid self-notification)
                if post.status == 'pending' and client != request.user:
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
                elif post.status != 'pending' and client != request.user:
                    # Original notification for drafts or other statuses (avoid self-notification)
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

                # TEMPORARY: Skip caching posts until cache issues are resolved
                # Cache the newly created post
                post_data = PostSerializer(post, context={'request': request}).data
                # cache.set(f"post:{post.id}", post_data, timeout=60*60)  # Cache for 1 hour
                # cache.set(f"post_detail:{post.id}", post_data, timeout=60*60)
                
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
    View to fetch all unique creators of posts that the user can see.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Build the query based on user role - same logic as ListPostsView
        if request.user.is_client:
            # Clients see only their own posts
            posts = Post.objects.filter(client=request.user)
            
        elif request.user.is_community_manager:
            # CMs see posts they created + posts for clients they're assigned to
            posts = Post.objects.filter(
                models.Q(creator=request.user) |  # Posts they created
                models.Q(client__assigned_communitymanagerstoclient=request.user)  # Posts for their assigned clients
            ).distinct()
            
        elif request.user.is_moderator:
            # Moderators see posts from their assigned CMs + posts for their assigned clients
            posts = Post.objects.filter(
                models.Q(creator__in=request.user.assigned_communitymanagers.all()) |  # Posts from their assigned CMs
                models.Q(client__assigned_moderator=request.user) |  # Posts for their assigned clients
                models.Q(creator=request.user)  # Posts they created themselves (if any)
            ).distinct()
            
        else:
            # Super admin or admin sees all posts
            posts = Post.objects.all()

        # Get the creators of these visible posts
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
    permission_classes = [IsAuthenticated, IsAssignedToPostOrAdmin]

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
        # TEMPORARY: Override caching for posts until cache issues are resolved
        # Check for bypass_cache parameter (always bypass for now)
        bypass_cache = True  # request.query_params.get('bypassCache', 'false').lower() == 'true'
        
        cache_key = f"user_posts:{request.user.id}"
        cached_data = None if bypass_cache else cache.get(cache_key)

        if cached_data is None:
            # Build the query based on user role
            if request.user.is_client:
                # Clients see only their own posts
                posts = Post.objects.filter(client=request.user)
                
            elif request.user.is_community_manager:
                # CMs see posts they created + ALL posts for their assigned clients
                assigned_clients = request.user.clients.all()
                
                posts = Post.objects.filter(
                    models.Q(creator=request.user) |  # Posts they created
                    models.Q(client__in=assigned_clients)  # All posts for their assigned clients
                ).distinct()
                
            elif request.user.is_moderator:
                # Moderators see posts from their assigned CMs + posts for their assigned clients
                posts = Post.objects.filter(
                    models.Q(creator__in=request.user.assigned_communitymanagers.all()) |  # Posts from their assigned CMs
                    models.Q(client__assigned_moderator=request.user) |  # Posts for their assigned clients
                    models.Q(creator=request.user)  # Posts they created themselves (if any)
                ).distinct()
                
                
            else:
                # Super admin or admin sees all posts
                posts = Post.objects.all()

            # Fetch posts with related client and creator objects
            posts = posts.select_related('client', 'creator').prefetch_related('media')

            # Serialize the posts with context
            serializer = PostSerializer(posts, many=True, context={'request': request})
            cached_data = serializer.data

            # TEMPORARY: Skip caching posts until cache issues are resolved
            # Cache the serialized data
            # cache.set(cache_key, cached_data, timeout=60 * 10)  
        return Response(cached_data, status=status.HTTP_200_OK)

class UpdatePostView(APIView):
    permission_classes = [IsAuthenticated, IsAssignedToPostOrAdmin]
    
    def get(self, request, post_id):  
        try:
            post = Post.objects.select_related('client', 'creator', 'feedback_by').prefetch_related('media').get(id=post_id)
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

            # Store original status to check if it was rejected
            original_status = post.status

            # Rest of your update logic...
            data = request.data.copy()
            media_files = request.FILES.getlist('media_files', [])
            existing_media_ids = request.data.getlist('existing_media', [])

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
                context={'request': request, 'existing_media': existing_media_ids}
            )

            if serializer.is_valid():
                # Check if this was a rejected post - if so, reset to pending
                if original_status == 'rejected':
                    # Reset status to pending for client approval
                    post.status = 'pending'
                    
                    # Clear previous feedback and rejection data
                    post.feedback = None
                    post.feedback_by = None
                    post.feedback_at = None
                    
                    # Reset approval/rejection flags for fresh workflow
                    post.is_client_approved = None
                    post.is_moderator_validated = None
                    post.client_approved_at = None
                    post.client_rejected_at = None
                    post.moderator_validated_at = None
                    post.moderator_rejected_at = None

                post = serializer.save(last_edited_by=request.user)

                
                if media_files:
                    self._handle_media_upload(post, media_files, request.user)

                # If post was rejected and is now pending, notify client for approval
                if original_status == 'rejected' and post.status == 'pending':
                    if post.client:
                        notify_user(
                            user=post.client,
                            title="Updated Post Pending Your Approval",
                            message=f"The post '{post.title}' has been updated and is now pending your approval.",
                            type="post_pending_approval"
                        )
                        
                        # Send email notification
                        from apps.accounts.tasks import send_celery_email
                        send_celery_email.delay(
                            'Updated Post Pending Your Approval',
                            f'Hello {post.client.full_name or post.client.email}, The post titled "{post.title}" has been updated and is now pending your approval. Please log in to review and approve or reject this post.',
                            [post.client.email],
                            fail_silently=False
                        )
                
                updated_data = PostSerializer(post, context={'request': request}).data
                # TEMPORARY: Skip caching posts until cache issues are resolved
                # cache.set(f"post:{post_id}", updated_data, timeout=60*60)
                # cache.set(f"post_detail:{post_id}", updated_data, timeout=60*60)
                # cache.delete(f"user_posts:{request.user.id}")
                # cache.delete(f"user_drafts:{request.user.id}")
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
    permission_classes = [IsAuthenticated, IsCommunityManager]

    def get(self, request):
        user = request.user
        cache_key = f"cm_posts:{user.id}"
        # TEMPORARY: Override caching for posts until cache issues are resolved
        cached_data = None  # cache.get(cache_key)
        
        if cached_data is None:
            # Get all clients assigned to this Community Manager
            assigned_clients = User.objects.filter(
                is_client=True,
                assigned_communitymanagerstoclient=user
            )
            
            # Get all posts for assigned clients (regardless of creator)
            posts = Post.objects.filter(
                client__in=assigned_clients
            ).select_related('client', 'creator').prefetch_related('media')
            
            serializer = PostSerializer(posts, many=True, context={'request': request})
            cached_data = serializer.data
            # TEMPORARY: Skip caching posts until cache issues are resolved
            # cache.set(cache_key, cached_data, timeout=60*10)  # 10 minutes
        
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
        # TEMPORARY: Override caching for posts until cache issues are resolved  
        # Check for bypass_cache parameter (always bypass for now)
        bypass_cache = True  # request.query_params.get('bypassCache', 'false').lower() == 'true'
        
        # Cache key for user drafts
        cache_key = f"user_drafts:{request.user.id}"
        cached_data = None if bypass_cache else cache.get(cache_key)

        if cached_data is None:
            # Build filter conditions using Q objects
            from django.db.models import Q
            
            # Admin and Super Admin can see all drafts
            if request.user.is_administrator or request.user.is_superadministrator:
                filter_conditions = Q(status='draft')
            
            # Clients cannot see drafts - they should only see approved/published content
            elif request.user.is_client:
                filter_conditions = Q(pk__in=[])  # Return empty queryset for clients
            
            else:
                # Start with drafts created by the current user
                filter_conditions = Q(creator=request.user, status='draft')
                
                # If user is a Community Manager, also include drafts from assigned moderators
                # but only for posts that belong to clients also assigned to this CM
                if request.user.is_community_manager:
                    # Get moderators assigned to this CM
                    assigned_moderators = request.user.moderators.all()
                    # Get clients assigned to this CM
                    assigned_clients = request.user.clients.all()
                    
                    if assigned_moderators.exists() and assigned_clients.exists():
                        # Only include drafts created by assigned moderators for assigned clients
                        filter_conditions |= Q(
                            creator__in=assigned_moderators, 
                            client__in=assigned_clients,
                            status='draft'
                        )
                
                # If user is a Moderator, also include drafts from assigned community managers
                elif request.user.is_moderator:
                    # Get community managers assigned to this moderator
                    assigned_cms = request.user.assigned_communitymanagers.all()
                    if assigned_cms.exists():
                        filter_conditions |= Q(creator__in=assigned_cms, status='draft')
            
            # Apply the filter and order by creation date
            drafts = Post.objects.filter(filter_conditions).distinct().order_by('-created_at')

            # Serialize the drafts
            serializer = PostSerializer(drafts, many=True, context={'request': request})
            cached_data = serializer.data

            # TEMPORARY: Skip caching drafts until cache issues are resolved
            # Cache the serialized drafts for 5 minutes
            # cache.set(cache_key, cached_data, 300)
            # cache.set(cache_key, cached_data, timeout=60 * 5)

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
    permission_classes = [IsAuthenticated, IsModeratorOrCMOrAdmin]

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
        Approve a post following the workflow:
        - Client approval: keeps status 'pending' but sets is_client_approved=True
        - Moderator validation: changes status to 'scheduled'
        - Moderator can override client approval and directly schedule
        """
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response(
                {"error": "Post not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions - client can approve their own posts, moderators can approve any
        if not (request.user.is_moderator or request.user.is_administrator or post.client == request.user):
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
        
        # Get feedback and override flag from request
        feedback = request.data.get('feedback', '')
        override_client = request.data.get('override_client', False)  # For moderator override
        
        post.last_edited_by = request.user
        if feedback:
            post.feedback = feedback
            post.feedback_by = request.user
            post.feedback_at = timezone.now()
        
        # Handle different approval scenarios based on your workflow
        if post.client == request.user:
            # Client approval: Stay pending but mark as client approved
            post.set_client_approved(request.user)
            # Status remains 'pending' - waiting for moderator validation
            approval_message = f"Post '{post.title}' approved by client. Waiting for moderator validation."
            
        elif request.user.is_moderator or request.user.is_administrator:
            if override_client or post.is_client_approved:
                # Moderator validates (either override or after client approval)
                post.status = 'scheduled'
                post.set_moderator_validated(request.user)
                approval_message = f"Post '{post.title}' validated by moderator and scheduled."
            else:
                # Moderator approval without client approval (shouldn't happen in normal flow)
                return Response(
                    {"error": "Post must be approved by client first, or use override_client=true"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        post.save()
        
        # Cache invalidation
        invalidate_cache(Post)
        invalidate_cache(Post, post_id)
        
        # Notify the creator about approval
        if post.creator and post.creator != request.user:
            if feedback:
                approval_message += f" Feedback: {feedback}"
            notify_user(
                user=post.creator,
                title="Post Approved",
                message=approval_message,
                type="post_approved"
            )
        
        # Notify the client about approval (if approved by moderator or admin)
        if post.client and post.client != request.user and (request.user.is_moderator or request.user.is_administrator):
            client_message = f"The post '{post.title}' has been validated by moderator and scheduled."
            if feedback:
                client_message += f" Feedback: {feedback}"
            notify_user(
                user=post.client,
                title="Post Validated",
                message=client_message,
                type="post_approved"
            )
        
        # Notify moderator if client approved the post (avoid double notification if creator is the assigned moderator)
        if request.user == post.client and post.creator and post.creator.is_moderator and post.creator != post.client.assigned_moderator:
            approval_message = f"The post '{post.title}' has been approved by the client and is now scheduled."
            if feedback:
                approval_message += f" Client feedback: {feedback}"
            notify_user(
                user=post.creator,
                title="Client Approved Post",
                message=approval_message,
                type="post_approved"
            )
        
        # Notify assigned moderator when client approves the post (only if different from creator)
        if request.user == post.client and post.client.assigned_moderator and post.client.assigned_moderator != post.creator:
            moderator_message = f"Post '{post.title}' approved by client. Waiting for your validation."
            if feedback:
                moderator_message += f" Client feedback: {feedback}"
            notify_user(
                user=post.client.assigned_moderator,
                title="Client Approved Post - Validation Needed",
                message=moderator_message,
                type="post_pending_validation"
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
        - For pending posts: Clients, moderators, and admins can reject
        - For scheduled posts: Only the client, assigned moderator, or administrator can reject
        - Community managers cannot reject scheduled posts
        """
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response(
                {"error": "Post not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions - client can reject their own posts, moderators and admins can reject any
        if not (request.user.is_moderator or request.user.is_administrator or post.client == request.user):
            return Response(
                {"error": "You are not authorized to reject this post."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if post can be rejected - pending and scheduled posts can be rejected
        if post.status not in ['pending', 'scheduled']:
            return Response(
                {"error": "Only pending or scheduled posts can be rejected."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Additional check: if post is scheduled, only specific users can reject it
        if post.status == 'scheduled':
            can_reject_scheduled = (
                request.user == post.client or  # The client
                request.user.is_administrator or  # Admin or super admin
                (request.user.is_moderator and post.client.assigned_moderator == request.user)  # Assigned moderator
            )
            
            if not can_reject_scheduled:
                return Response(
                    {"error": "Only the client, assigned moderator, or administrator can reject scheduled posts."}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Get feedback from request
        feedback = request.data.get('feedback', 'No feedback provided')
        
        # Update post status to rejected
        post.status = 'rejected'
        post.last_edited_by = request.user
        post.feedback = feedback
        post.feedback_by = request.user
        post.feedback_at = timezone.now()
        
        # Set appropriate rejection timestamp based on who rejected
        if post.client == request.user:
            post.set_client_rejected(request.user)
        elif request.user.is_moderator or request.user.is_administrator:
            post.set_moderator_rejected(request.user)
        
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
        
        # Notify the client about rejection (if rejected by moderator or admin)
        if post.client and post.client != request.user and (request.user.is_moderator or request.user.is_administrator):
            notify_user(
                title=f"Post '{post.title}' Rejected",
                user=post.client,
                message=f"The post '{post.title}' has been rejected. Feedback: {feedback}",
                type="post_rejected"
            )
        
        # Notify moderator if client rejected the post (avoid double notification if creator is the assigned moderator)
        if request.user == post.client and post.creator and post.creator.is_moderator and post.creator != post.client.assigned_moderator:
            notify_user(
                title=f"Post '{post.title}' Rejected",
                user=post.creator,
                message=f"The post '{post.title}' has been rejected by the client. Feedback: {feedback}",
                type="post_rejected"
            )
        
        # Notify assigned moderator when client rejects the post (only if different from creator)
        if request.user == post.client and post.client.assigned_moderator and post.client.assigned_moderator != post.creator:
            notify_user(
                title=f"Post '{post.title}' Rejected by Client",
                user=post.client.assigned_moderator,
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
        - Moderators and Administrators see all pending posts
        - CMs see pending posts for their assigned clients
        """
        cache_key = f"pending_posts:{request.user.id}"
        # TEMPORARY: Override caching for posts until cache issues are resolved
        cached_data = None  # cache.get(cache_key)

        if cached_data is None:
            if request.user.is_client:
                # Clients see their own pending posts
                pending_posts = Post.objects.filter(
                    client=request.user,
                    status='pending'
                ).select_related('creator', 'client').prefetch_related('media')
            
            elif request.user.is_moderator or request.user.is_administrator:
                # Moderators and Administrators see all pending posts
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

            # TEMPORARY: Skip caching pending posts until cache issues are resolved
            # Cache the serialized data for 5 minutes
            # cache.set(cache_key, cached_data, timeout=60 * 5)

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


class GetPostByIdView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, post_id):
        """
        Retrieve a single post by its ID.
        """
        try:
            post = Post.objects.select_related('client', 'creator', 'feedback_by').prefetch_related('media').get(id=post_id)
            
            # Check if user has permission to view this post
            # Allow access if:
            # 1. User is assigned to the post (covers client, assigned CM, assigned moderator)
            # 2. User is a moderator or administrator
            # 3. User is the creator (community manager who created the post)
            # 4. User is a CM assigned to the client of this post
            # 5. User is a CM and the post creator is their assigned moderator
            cm_assigned_to_client = (
                request.user.is_community_manager and 
                post.client and 
                post.client.assigned_communitymanagerstoclient.filter(id=request.user.id).exists()
            )
            
            cm_can_see_mod_post = (
                request.user.is_community_manager and 
                post.creator and 
                post.creator == request.user.assigned_moderator and
                post.client and 
                post.client.assigned_communitymanagerstoclient.filter(id=request.user.id).exists()
            )
            
            if not (post.is_user_assigned(request.user) or 
                    request.user.is_moderator or 
                    request.user.is_administrator or
                    post.creator == request.user or
                    cm_assigned_to_client or
                    cm_can_see_mod_post):
                return Response(
                    {"error": "You don't have permission to view this post"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = PostSerializer(post, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Post.DoesNotExist:
            return Response(
                {"error": "Post not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PublishPostView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, post_id):
        """
        Publish a post by changing its status to 'published'.
        Only moderators and authorized users can publish posts.
        """
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response(
                {"error": "Post not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions - moderators and admins can publish any post, clients can publish their own
        if not (request.user.is_moderator or request.user.is_administrator or post.client == request.user):
            return Response(
                {"error": "You are not authorized to publish this post."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if post is in scheduled status
        if post.status != 'scheduled':
            return Response(
                {"error": "Only scheduled posts can be published."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update post status to published
        post.status = 'published'
        post.set_published(request.user)
        post.save()
        
        # Cache invalidation
        invalidate_cache(Post)
        invalidate_cache(Post, post_id)
        
        # Notify the creator about publication
        if post.creator and post.creator != request.user:
            notify_user(
                user=post.creator,
                title="Post Published",
                message=f"Your post '{post.title}' has been published successfully!",
                type="post_published"
            )
        
        # Notify the client about publication (if published by moderator or admin)
        if post.client and post.client != request.user and (request.user.is_moderator or request.user.is_administrator):
            notify_user(
                user=post.client,
                title="Post Published",
                message=f"The post '{post.title}' has been published successfully!",
                type="post_published"
            )
        
        response_data = {
            "message": "Post published successfully.",
            "post": PostSerializer(post).data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class ResubmitPostView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, post_id):
        """
        Resubmit a rejected post by changing its status to 'pending'.
        Only the creator or client can resubmit rejected posts.
        """
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response(
                {"error": "Post not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions - creator or client can resubmit
        if not (post.creator == request.user or post.client == request.user):
            return Response(
                {"error": "You are not authorized to resubmit this post."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if post is in rejected status
        if post.status != 'rejected':
            return Response(
                {"error": "Only rejected posts can be resubmitted."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update post status to pending and reset workflow flags
        post.status = 'pending'
        post.last_edited_by = request.user
        
        # Clear previous feedback when resubmitting
        post.feedback = None
        post.feedback_by = None
        post.feedback_at = None
        
        # Reset approval/rejection flags for fresh workflow
        post.is_client_approved = None
        post.is_moderator_validated = None
        post.client_approved_at = None
        post.client_rejected_at = None
        post.moderator_validated_at = None
        post.moderator_rejected_at = None
        
        post.save()
        
        # Cache invalidation
        invalidate_cache(Post)
        invalidate_cache(Post, post_id)
        
        # Notify client about resubmission for approval
        if post.client:
            notify_user(
                user=post.client,
                title="Post Resubmitted for Your Approval",
                message=f"The post '{post.title}' has been resubmitted and is pending your approval. Please review and approve or reject it.",
                type="post_pending_approval"
            )
            
            # Send email notification to client
            from apps.accounts.tasks import send_celery_email
            send_celery_email.delay(
                'Post Resubmitted for Your Approval',
                f'Hello {post.client.full_name or post.client.email}, The post titled "{post.title}" has been resubmitted and is now pending your approval. Please log in to review and approve or reject this post.',
                [post.client.email],
                fail_silently=False
            )
        
        # Notify moderators about resubmission (avoid double notification if creator is the assigned moderator)
        if post.client and post.client.assigned_moderator and post.client.assigned_moderator != post.creator:
            notify_user(
                user=post.client.assigned_moderator,
                title="Post Resubmitted",
                message=f"The post '{post.title}' has been resubmitted for review.",
                type="post_resubmitted"
            )
        
        response_data = {
            "message": "Post resubmitted successfully.",
            "post": PostSerializer(post).data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class CancelApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, post_id):
        """
        Cancel approval of a scheduled post by changing its status to 'rejected'.
        Only moderators can cancel approval.
        """
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response(
                {"error": "Post not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions - moderators and admins can cancel approval
        if not (request.user.is_moderator or request.user.is_administrator):
            return Response(
                {"error": "You are not authorized to cancel approval for this post."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if post is in scheduled status
        if post.status != 'scheduled':
            return Response(
                {"error": "Only scheduled posts can have their approval cancelled."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get feedback from request
        feedback = request.data.get('feedback', 'Approval cancelled')
        
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
        
        # Notify the creator about cancellation
        if post.creator and post.creator != request.user:
            notify_user(
                user=post.creator,
                title="Post Approval Cancelled",
                message=f"The approval for post '{post.title}' has been cancelled. Feedback: {feedback}",
                type="post_approval_cancelled"
            )
        
        # Notify the client about cancellation
        if post.client and post.client != request.user:
            notify_user(
                user=post.client,
                title="Post Approval Cancelled",
                message=f"The approval for post '{post.title}' has been cancelled. Feedback: {feedback}",
                type="post_approval_cancelled"
            )
        
        response_data = {
            "message": "Post approval cancelled successfully.",
            "post": PostSerializer(post).data,
            "feedback": feedback
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

class ModeratorValidatePostView(APIView):
    """
    Moderator validation view - validates posts that are pending with client approval
    or can override client approval requirement.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, post_id):
        """
        Validate a post by moderator following the workflow:
        - Can validate posts that are pending + client approved
        - Can override client approval with override_client=true
        """
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response(
                {"error": "Post not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions - only moderators and admins can validate
        if not (request.user.is_moderator or request.user.is_administrator or request.user.is_superadministrator):
            return Response(
                {"error": "You are not authorized to validate this post."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if post is in pending status
        if post.status != 'pending':
            return Response(
                {"error": "Only pending posts can be validated."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get parameters from request
        feedback = request.data.get('feedback', '')
        override_client = request.data.get('override_client', False)
        
        # Check workflow rules
        if not override_client and not post.is_client_approved:
            return Response(
                {"error": "Post must be approved by client first, or use override_client=true"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate the post
        post.status = 'scheduled'
        post.last_edited_by = request.user
        if feedback:
            post.feedback = feedback
            post.feedback_by = request.user
            post.feedback_at = timezone.now()
        
        post.set_moderator_validated(request.user)
        post.save()
        
        # Cache invalidation
        invalidate_cache(Post)
        invalidate_cache(Post, post_id)
        
        # Notifications
        validation_message = f"Post '{post.title}' validated by moderator and scheduled."
        if feedback:
            validation_message += f" Feedback: {feedback}"
        
        # Notify the creator
        if post.creator and post.creator != request.user:
            notify_user(
                user=post.creator,
                title="Post Validated",
                message=validation_message,
                type="post_validated"
            )
        
        # Notify the client
        if post.client and post.client != request.user:
            notify_user(
                user=post.client,
                title="Post Validated",
                message=validation_message,
                type="post_validated"
            )
        
        # Notify assigned moderator when admin validates the post (avoid notifying if they are the creator)
        if (request.user.is_administrator or request.user.is_superadministrator) and post.client and post.client.assigned_moderator and post.client.assigned_moderator != request.user and post.client.assigned_moderator != post.creator:
            admin_validation_message = f"Post '{post.title}' validated by admin and scheduled."
            if feedback:
                admin_validation_message += f" Admin feedback: {feedback}"
            notify_user(
                user=post.client.assigned_moderator,
                title="Post Validated by Admin",
                message=admin_validation_message,
                type="post_validated"
            )
        
        response_data = {
            "message": "Post validated successfully.",
            "post": PostSerializer(post).data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


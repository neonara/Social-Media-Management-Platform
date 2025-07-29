from django.urls import path
from .views import UpdatePostToDraftView, GetPostCreatorsView, FetchCMClientPostsView, SaveDraftView, CreatePostView, ListPostsView, UpdatePostView, MediaListView, MediaDetailView, FetchDraftsView, DeletePostView, ApprovePostView, RejectPostView, FetchPendingPostsView, PostFeedbackView, GetPostByIdView, PublishPostView, ResubmitPostView, CancelApprovalView

urlpatterns = [
    path('posts/', ListPostsView.as_view(), name='list-posts'),
    path('posts/creators/', GetPostCreatorsView.as_view(), name='get-post-creators'),  
    path('posts/create/', CreatePostView.as_view(), name='create-post'), 
    path('posts/client/<int:client_id>/create/', CreatePostView.as_view(), name='create-post-for-client'),
    path('posts/<int:post_id>/', UpdatePostView.as_view(), name='update-post'),
    path('posts/<int:post_id>/', GetPostByIdView.as_view(), name='get-post-by-id'),
    path('posts/<int:post_id>/delete/', DeletePostView.as_view(), name='delete-post'),  
    path('posts/<int:post_id>/approve/', ApprovePostView.as_view(), name='approve-post'),
    path('posts/<int:post_id>/reject/', RejectPostView.as_view(), name='reject-post'),
    path('posts/<int:post_id>/publish/', PublishPostView.as_view(), name='publish-post'),
    path('posts/<int:post_id>/resubmit/', ResubmitPostView.as_view(), name='resubmit-post'),
    path('posts/<int:post_id>/cancel-approval/', CancelApprovalView.as_view(), name='cancel-approval'),
    path('posts/<int:post_id>/feedback/', PostFeedbackView.as_view(), name='post-feedback'),
    path('posts/drafts/', FetchDraftsView.as_view(), name='fetch-drafts'),
    path('posts/pending/', FetchPendingPostsView.as_view(), name='fetch-pending-posts'),
    path('posts/save-draft/', SaveDraftView.as_view(), name='save-draft'),
    path('posts/cm/clients/', FetchCMClientPostsView.as_view(), name='fetch-cm-client-posts'),
    path('posts/<int:post_id>/to-draft/', UpdatePostToDraftView.as_view(), name='update-post-to-draft'),

    # Media
    path('media/', MediaListView.as_view(), name='media-list'),
    path('media/<int:pk>/', MediaDetailView.as_view(), name='media-detail'),
]
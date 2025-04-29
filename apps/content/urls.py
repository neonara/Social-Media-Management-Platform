from django.urls import path
from .views import SaveDraftView, CreatePostView, ListPostsView, UpdatePostView, MediaListView, MediaDetailView, FetchDraftsView, DeletePostView  # Add this import

urlpatterns = [
    path('posts/', ListPostsView.as_view(), name='list-posts'),
    path('posts/create/', CreatePostView.as_view(), name='create-post'),  # New endpoint
    path('posts/client/<int:client_id>/create/', CreatePostView.as_view(), name='create-post-for-client'),
    path('posts/<int:post_id>/', UpdatePostView.as_view(), name='update-post'),
    path('posts/<int:post_id>/delete/', DeletePostView.as_view(), name='delete-post'),  
    path('posts/drafts/', FetchDraftsView.as_view(), name='fetch-drafts'),
    path('posts/save-draft/', SaveDraftView.as_view(), name='save-draft'),

    # Media
    path('media/', MediaListView.as_view(), name='media-list'),
    path('media/<int:pk>/', MediaDetailView.as_view(), name='media-detail'),
]
from django.urls import path

from .views import AssignCommunityManagerToModeratorView,FetchEmails, AssignModeratorToClientView,RemoveModeratorFromClientView,RemoveCommunityManagerFromModeratorView, ListUsers, ManageAssignedCommunityManagerView, PasswordResetRequestView, UserLoginView, UserUpdateUserView, CreateUserView, FirstTimePasswordChangeView, LogoutUserView, AdminDeleteUserView, PasswordResetConfirmView

urlpatterns = [
    # Authentication URLs
    path('auth/login/', UserLoginView.as_view(), name='user-login'), 
    path('auth/logout/', LogoutUserView.as_view(), name='logout'),
    path('auth/register/', CreateUserView.as_view(), name='create-user'),
    path('auth/reset-password/', PasswordResetRequestView.as_view(), name='reset_password'),
    path('auth/reset/<str:uid64>/<str:token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('auth/first-time-password-change/', FirstTimePasswordChangeView.as_view(), name='first-time-password-change'),
    path('auth/reset-password-confirm/<uid>/<token>/', PasswordResetConfirmView.as_view(), name='reset-password-confirm'),
    
    # User management URLs
    path('users/fetchemail/', FetchEmails.as_view(), name='fetch-email'),
    path('users/', ListUsers.as_view(), name='user-list'),
    path('users/update/<int:user_id>/', UserUpdateUserView.as_view(), name='user-update'),
    path('users/delete/<int:user_id>/', AdminDeleteUserView.as_view(), name='user-delete'),
    path('users/update-profile/', UserUpdateUserView.as_view(), name='update-profile'),
    
    # Assignment URLs
    path("clients/<int:client_id>/moderator/", AssignModeratorToClientView.as_view(), name="assign-moderator"),
    path("moderators/<int:moderator_id>/community-manager/", AssignCommunityManagerToModeratorView.as_view(), name="assign-community-manager"),
    path("moderators/assigned-community-manager/", ManageAssignedCommunityManagerView.as_view(), name="manage-assigned-community-manager"),
    
    path('clients/<int:client_id>/moderator/remove/', RemoveModeratorFromClientView.as_view()),
    path('moderators/<int:moderator_id>/community-manager/<int:cm_id>/remove/', RemoveCommunityManagerFromModeratorView.as_view()),


]
from django.urls import path

from .views import ValidateTokenView, ValidateRoleView, ClientFetchModeratorAndCMsView, AssignedModeratorsAndClientsView, AssignedClientsView, AssignCommunityManagerToModeratorView ,CurrentUserView,FetchEmails, AssignModeratorToClientView, RemoveModeratorFromClientView,RemoveCommunityManagerFromModeratorView, ListUsers, PasswordResetRequestView, UserLoginView, UpdateUserView, CreateUserView, FirstTimePasswordChangeView, LogoutUserView, AdminDeleteUserView, PasswordResetConfirmView, GetUserByIdView, ClientAssignedCommunityManagersView, EligibleCMsForClient, RemoveClientCommunityManagersView, AssignedModeratorClientsView, AssignCMToClientView, CreateCMView, AssignedModeratorCommunityManagersView  

urlpatterns = [
    # Authentication URLs
    path('auth/login/', UserLoginView.as_view(), name='user-login'), 
    path('auth/logout/', LogoutUserView.as_view(), name='logout'),
    path('auth/register/', CreateUserView.as_view(), name='create-user'),
    path('auth/reset-password/', PasswordResetRequestView.as_view(), name='reset_password'),
    path('auth/first-time-password-change/', FirstTimePasswordChangeView.as_view(), name='first-time-password-change'),
    
    # Security validation endpoints
    path('auth/validate-token/', ValidateTokenView.as_view(), name='validate-token'),
    path('auth/validate-role/', ValidateRoleView.as_view(), name='validate-role'),
    
    path('reset-password-confirm/<uid>/<token>/', PasswordResetConfirmView.as_view(), name='reset-password-confirm'),
    
    # User management URLs
    
    path('user/profile/', CurrentUserView.as_view(), name='current_user'),
    path('user/<int:user_id>/', GetUserByIdView.as_view(), name='user-detail'),
    path('users/fetchemail/', FetchEmails.as_view(), name='fetch-email'),
    path('users/', ListUsers.as_view(), name='user-list'),
    path('users/update/<int:user_id>/', UpdateUserView.as_view(), name='user-update'),
    path('users/delete/<int:user_id>/', AdminDeleteUserView.as_view(), name='user-delete'),
    
    # Assignment URLs
    path("clients/<int:client_id>/moderator/", AssignModeratorToClientView.as_view(), name="assign-moderator"),
    path("moderators/<int:moderator_id>/community-manager/", AssignCommunityManagerToModeratorView.as_view(), name="assign-community-manager"),
    path('clients/<int:client_id>/assign-cm/', AssignCMToClientView.as_view(), name='assign-client-cms'),
    
    #remove assignments
    path('clients/<int:client_id>/community-managers/remove/',RemoveClientCommunityManagersView.as_view(), name='assign-client-cms'),
    path('clients/<int:client_id>/moderator/remove/', RemoveModeratorFromClientView.as_view()),
    path('moderators/<int:moderator_id>/community-manager/<int:cm_id>/remove/', RemoveCommunityManagerFromModeratorView.as_view()), 
    
    #fetched assignement
     path('user/<int:user_id>/', GetUserByIdView.as_view(), name='user-detail'),
    path('moderators/assigned-cms/', AssignedModeratorCommunityManagersView.as_view(), name='moderator-assigned-cms'),
    path('moderators/assignedClients/', AssignedModeratorClientsView.as_view()),
    path('clients/<int:client_id>/assigned-cms/', ClientAssignedCommunityManagersView.as_view(), name='client_assigned_cms'),
    
    path('community-manager/assignments/', AssignedModeratorsAndClientsView.as_view(), name='assigned-moderators-clients'),
    path('client/assignments/', ClientFetchModeratorAndCMsView.as_view(), name='client-moderator-and-cms'),
     
    path('clients/<int:client_id>/eligible-cms/', EligibleCMsForClient.as_view(), name='eligible-cms-for-client'),
    path('clients/assigned/', AssignedClientsView.as_view(), name='assigned-clients'),
    
    path('moderators/createCM/', CreateCMView.as_view(), name='create-community-manager'),

]
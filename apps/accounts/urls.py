from django.urls import path
from .views import  AssignModeratorToClientView, PasswordResetConfirmView, PasswordResetRequestView,  UserLoginView, AdminUpdateUserView,AssignCommunityManagerToModeratorView, ManageAssignedCommunityManagerView
from .views import LogoutUserView

urlpatterns = [
    path('login/', UserLoginView.as_view(), name='user-login'), 
    path('logout/', LogoutUserView.as_view(), name='logout'),
    path('reset_password/', PasswordResetRequestView.as_view(), name='reset_password'),
    path("reset-password-confirm/<uid>/<token>/", PasswordResetConfirmView.as_view(), name="reset-password-confirm"),
    path('update-profile/', AdminUpdateUserView.as_view(), name='update-profile'),
    path('users/update/<int:user_id>/', AdminUpdateUserView.as_view(), name='user-update'),
    path("clients/<int:client_id>/moderator", AssignModeratorToClientView.as_view(), name="assign-moderator"),
    path("moderators/<int:moderator_id>/community-manager", AssignCommunityManagerToModeratorView.as_view(), name="assign-community-manager"),
    path("moderators/assigned-community-manager", ManageAssignedCommunityManagerView.as_view(), name="manage-assigned-community-manager"),



]
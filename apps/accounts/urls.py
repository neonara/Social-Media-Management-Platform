from django.urls import path

from .views import ChangePasswordView, ListUsers, PasswordResetRequestView, SetNewPasswordView, UserLoginView, AdminUpdateUserView, CreateUserView, FirstTimePasswordChangeView, LogoutUserView, AdminDeleteUserView

from .views import  PasswordResetConfirmView, PasswordResetRequestView,  UserLoginView, AdminUpdateUserView
from .views import LogoutUserView

urlpatterns = [
    # Authentication URLs
    path('auth/login/', UserLoginView.as_view(), name='user-login'), 
    path('auth/logout/', LogoutUserView.as_view(), name='logout'),
    path('auth/register/', CreateUserView.as_view(), name='create-user'),
    path('auth/reset-password/', PasswordResetRequestView.as_view(), name='reset_password'),
    path('auth/reset/<str:uid64>/<str:token>/', SetNewPasswordView.as_view(), name='password_reset_confirm'),
    path('auth/set-newpassword/<int:user_id>/<str:token>/', SetNewPasswordView.as_view(), name='set_new_password'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('auth/first-time-password-change/', FirstTimePasswordChangeView.as_view(), name='first-time-password-change'),
    path('auth/reset-password-confirm/<uid>/<token>/', PasswordResetConfirmView.as_view(), name='reset-password-confirm'),
    
    # User management URLs
    path('users/', ListUsers.as_view(), name='user-list'),
    path('users/<int:user_id>/', AdminUpdateUserView.as_view(), name='user-update'),
    path('users/<int:user_id>/', AdminDeleteUserView.as_view(), name='user-delete'),
    path('users/update-profile/', AdminUpdateUserView.as_view(), name='update-profile'),
]

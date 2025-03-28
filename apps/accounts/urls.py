from django.urls import path
from .views import ChangePasswordView, ListUsers, PasswordResetRequestView, SetNewPasswordView, UserLoginView, AdminUpdateUserView, CreateUserView, FirstTimePasswordChangeView, LogoutUserView

urlpatterns = [
    path('login/', UserLoginView.as_view(), name='user-login'), 
    path('logout/', LogoutUserView.as_view(), name='logout'),
    path('reset_password/', PasswordResetRequestView.as_view(), name='reset_password'),
    path('reset/<str:uid64>/<str:token>/', SetNewPasswordView.as_view(), name='password_reset_confirm'),
    path('set-newpassword/<int:user_id>/<str:token>/', SetNewPasswordView.as_view(), name='set_new_password'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('update-profile/', AdminUpdateUserView.as_view(), name='update-profile'),
    path('users/update/<int:user_id>/', AdminUpdateUserView.as_view(), name='user-update'),
    path('create-user/', CreateUserView.as_view(), name='create-user'),
    path('first-time-password-change/', FirstTimePasswordChangeView.as_view(), name='first-time-password-change'),
    path('users/', ListUsers.as_view(), name='user-list'),
]
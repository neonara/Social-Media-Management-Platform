from django.urls import path
from .views import  PasswordResetConfirmView, PasswordResetRequestView,  UserLoginView, AdminUpdateUserView
from .views import LogoutUserView

urlpatterns = [
    path('login/', UserLoginView.as_view(), name='user-login'), 
    path('logout/', LogoutUserView.as_view(), name='logout'),
    path('reset_password/', PasswordResetRequestView.as_view(), name='reset_password'),
    path("reset-password-confirm/<uid>/<token>/", PasswordResetConfirmView.as_view(), name="reset-password-confirm"),
    path('update-profile/', AdminUpdateUserView.as_view(), name='update-profile'),
    path('users/update/<int:user_id>/', AdminUpdateUserView.as_view(), name='user-update'),

]
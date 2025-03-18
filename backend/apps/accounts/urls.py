from django.urls import path
from .views import PasswordResetRequestView, SetNewPasswordView, UserLoginView
from .views import LogoutUserView

urlpatterns = [
    path('login/', UserLoginView.as_view(), name='user-login'), 
    path('logout/', LogoutUserView.as_view(), name='logout'),
    path('reset_password/', PasswordResetRequestView.as_view(), name='reset_password'),
    path('reset/<str:uid64>/<str:token>/', SetNewPasswordView.as_view(), name='password_reset_confirm'),
]
    
    
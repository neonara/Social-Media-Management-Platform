from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def home(request):
    return HttpResponse("Welcome to the Social Media Management Platform!")

urlpatterns = [
    path('', home, name='home'),  
    path('admin/', admin.site.urls),  
    path('api/auth/', include('apps.accounts.urls')),  
]
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.conf.urls.static import static
from django.conf import settings

def home(request):
    return HttpResponse("Welcome to the Social Media Management Platform!")

urlpatterns = [
    path('', home, name='home'),  
    path('admin/', admin.site.urls),  
    path('api/', include('apps.accounts.urls')),  
    path('api/content/', include('apps.content.urls')),  
    path('api/', include('apps.social_media.urls')),  
    path('api/', include('apps.notifications.urls')),  
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
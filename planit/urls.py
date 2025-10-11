from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.conf.urls.static import static
from django.conf import settings
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

def home(request):
    return HttpResponse("Welcome to Plan'it !")

urlpatterns = [
    path('', home, name='home'),  
    path('admin/', admin.site.urls),  
    path('api/', include('apps.accounts.urls')),  
    path('api/content/', include('apps.content.urls')),  
    path('api/', include('apps.social_media.urls')),  
    path('api/', include('apps.notifications.urls')),  
    path('api-auth/', include('rest_framework.urls')),  # DRF login/logout
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
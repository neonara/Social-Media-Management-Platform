import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'
# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-default-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG =True

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# settings.py
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "TIMEOUT": None, # Set to None for no timeout
    }
}

# Application definition

INSTALLED_APPS = [
    'apps.accounts',         
    'apps.content',           
    # 'apps.planning',          
    # 'apps.analytics',        
    'apps.notifications',    
    # 'apps.ai_integration',   
    'apps.social_media',    
    'apps.collaboration',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels'
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #'apps.core.middleware.MediaResponseHeadersMiddleware',
]
DATA_UPLOAD_MAX_MEMORY_SIZE = 1048576000  # 1000 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 1048576000  # 1000 MB
# CSRF Settings
CSRF_COOKIE_SAMESITE = 'Lax'  # Use 'None' if using HTTPS
CSRF_COOKIE_SECURE = False    # Set to True in production with HTTPS
CSRF_COOKIE_HTTPONLY = False  # Must be False to allow access via JavaScript

# CORS Settings
CORS_ALLOW_ALL_ORIGINS = False  # Restrict to specific origins in production
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Add your Next.js frontend URL
]
CORS_ALLOW_CREDENTIALS = True  # Allow cookies to be sent with requests

# CSP_IMG_SRC = ("'self'", "data:", "http://localhost:8000")

# Allow all needed HTTP methods
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Allow all headers for CORS
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'default-src': (
            "'self'",
            'http://localhost:3000',
            'http://localhost:8000',
        ),
        'img-src': (
            "'self'",
            'data:',
            'http://localhost:8000',
        ),
        'media-src': (
            "'self'",
            'data:',
            'http://localhost:8000',
        ),
        'script-src': (
            "'self'",
            'http://localhost:3000',
            'http://localhost:8000',
        ),
    }
}

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:8000',
]
WILL_MIGRATE = False
ROOT_URLCONF = 'social_media_management.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR)],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'social_media_management.wsgi.application'
ASGI_APPLICATION = 'social_media_management.asgi.application'


# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'social_media_platform'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'root'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

REST_FRAMEWORK = {
    'NON_FIELD_ERRORS_KEY': 'error',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # 'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=90),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_USER_MODEL = 'accounts.User'
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  
MEDIA_ROOT = os.path.join(BASE_DIR, 'media') 

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),  # Optional: for custom static dirs
]

# For WhiteNoise compression (optional but recommended)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Frontend URL for password reset
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# Development flag
DEBUG_EMAIL = DEBUG

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",  # or use redis://redis:6379/1 in Docker-only networks
        # "LOCATION": "redis://host.docker.internal:6379/1",  # or use redis://redis:6379/1 in Docker-only networks
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

SESSION_ENGINE =  "django.contrib.sessions.backends.db"
SESSION_CACHE_ALIAS = "default"

SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = False  # Set to True in production

FACEBOOK_GRAPH_API_VERSION = 'v21.0'
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")
FACEBOOK_REDIRECT_URI = "http://localhost:8000/api/facebook/callback/"
FACEBOOK_SCOPES = "pages_show_list,pages_manage_posts,pages_read_engagement,pages_read_user_content,pages_manage_engagement,email,public_profile"

INSTAGRAM_SCOPES = "instagram_basic,instagram_content_publish,pages_show_list"
INSTAGRAM_REDIRECT_URI = "http://localhost:8000/api/instagram/callback/"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
            }
        }
    }

CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'  
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

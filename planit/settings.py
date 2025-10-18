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

FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:8000')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# settings.py
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = os.environ.get('REDIS_PORT', '6379')

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
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
    'drf_spectacular',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'unfold', 
    "unfold.contrib.filters",  # optional, if special filters are needed
    "unfold.contrib.forms",  # optional, if special form elements are needed
    "unfold.contrib.inlines",  # optional, if special inlines are needed
    "unfold.contrib.import_export",  # optional, if django-import-export package is used
    "unfold.contrib.guardian",  # optional, if django-guardian package is used
    "unfold.contrib.simple_history",  # optional, if django-simple-history package is used
    "unfold.contrib.location_field",  # optional, if django-location-field package is used
    "unfold.contrib.constance",  # optional, if django-constance package is used
    'login_history',
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
    'apps.accounts.authentication.SecurityMiddleware',  # Custom security middleware
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #'apps.core.middleware.MediaResponseHeadersMiddleware',
]
DATA_UPLOAD_MAX_MEMORY_SIZE = 1048576000  # 1000 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 1048576000  # 1000 MB
# CSRF Settings
CSRF_COOKIE_SAMESITE = 'Lax'  # Use 'None' if using HTTPS
CSRF_COOKIE_SECURE = not DEBUG    # Set to True in production with HTTPS
CSRF_COOKIE_HTTPONLY = False  # Must be False to allow access via JavaScript

# CORS Settings
CORS_ALLOW_ALL_ORIGINS = False  # Restrict to specific origins in production
CORS_ALLOWED_ORIGINS = [
    FRONTEND_URL,
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
            FRONTEND_URL,
            BACKEND_URL,
        ),
        'img-src': (
            "'self'",
            'data:',
            BACKEND_URL,
        ),
        'media-src': (
            "'self'",
            'data:',
            BACKEND_URL,
        ),
        'script-src': (
            "'self'",
            FRONTEND_URL,
            BACKEND_URL,
        ),
    }
}

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = [
    FRONTEND_URL,
    BACKEND_URL,
]
WILL_MIGRATE = False
ROOT_URLCONF = 'planit.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'planit.wsgi.application'
ASGI_APPLICATION = 'planit.asgi.application'


# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'planit_db'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'root'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# Build authentication classes list dynamically
DEFAULT_AUTHENTICATION_CLASSES = [
    'apps.accounts.authentication.JWTCookieAuthentication',  # Cookie-based JWT auth (primary)
    'apps.accounts.authentication.JWTHeaderAuthentication',  # Header-based JWT auth (secondary)
]

# Add SessionAuthentication only in DEBUG mode
if DEBUG:
    DEFAULT_AUTHENTICATION_CLASSES.append('rest_framework.authentication.SessionAuthentication')

REST_FRAMEWORK = {
    'NON_FIELD_ERRORS_KEY': 'error',
    'DEFAULT_AUTHENTICATION_CLASSES': DEFAULT_AUTHENTICATION_CLASSES,
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # Default to requiring auth
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',  # Enable browsable API
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Spectacular settings for API documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'PlanIt API',
    'DESCRIPTION': 'API documentation for PlanIt Social Media Management Platform',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/',
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayRequestDuration': True,
        'displayOperationId': False,
        'defaultModelsExpandDepth': 1,
        'defaultModelExpandDepth': 1,
        'tryItOutEnabled': True,
    },
    'AUTHENTICATION_WHITELIST': [
        'apps.accounts.authentication.JWTCookieAuthentication',
        'apps.accounts.authentication.JWTHeaderAuthentication',
    ],
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'SERVE_AUTHENTICATION': [],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=90),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'ALGORITHM': 'HS256',  # Ensure strong algorithm
    'SIGNING_KEY': SECRET_KEY,  # Use secret key for signing
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JSON_ENCODER': None,
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=90),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
    'TOKEN_OBTAIN_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenObtainPairSerializer',
    'TOKEN_REFRESH_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenRefreshSerializer',
    'TOKEN_VERIFY_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenVerifySerializer',
    'TOKEN_BLACKLIST_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenBlacklistSerializer',
    'SLIDING_TOKEN_OBTAIN_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenObtainSlidingSerializer',
    'SLIDING_TOKEN_REFRESH_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenRefreshSlidingSerializer',
}

SESSION_COOKIE_AGE = 3600  # Regular session (1 hour in seconds)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Default behavior for non-remember-me

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
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media') 

# Only include static directory if it exists
STATICFILES_DIRS = []
static_dir = os.path.join(BASE_DIR, 'static')
if os.path.exists(static_dir):
    STATICFILES_DIRS.append(static_dir)

# For WhiteNoise compression (optional but recommended)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# WhiteNoise configuration for media files (works with Daphne/ASGI)
WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_USE_FINDERS = DEBUG
WHITENOISE_ALLOW_ALL_ORIGINS = DEBUG  # Allow CORS for media files in development
WHITENOISE_SKIP_COMPRESS_EXTENSIONS = ('jpg', 'jpeg', 'png', 'gif', 'webp', 'zip', 'gz', 'tgz', 'bz2', 'tbz', 'xz', 'br', 'swf', 'flv', 'woff', 'woff2')
# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
# Use console backend for development (when DEBUG=True), SMTP for production
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Development flag
DEBUG_EMAIL = DEBUG

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

SESSION_ENGINE =  "django.contrib.sessions.backends.db"
SESSION_CACHE_ALIAS = "default"

SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG  # Set to True in production

FACEBOOK_GRAPH_API_VERSION = 'v21.0'
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")
FACEBOOK_REDIRECT_URI = f"{BACKEND_URL}/api/facebook/callback/"
FACEBOOK_SCOPES = "pages_show_list,pages_manage_posts,pages_read_engagement,pages_read_user_content,pages_manage_engagement,business_management,pages_manage_metadata,pages_manage_instant_articles,email,public_profile"

INSTAGRAM_SCOPES = "instagram_basic,instagram_content_publish,instagram_manage_insights,pages_show_list,business_management"
INSTAGRAM_REDIRECT_URI = f"{BACKEND_URL}/api/instagram/callback/"

LINKEDIN_REDIRECT_URI = f"{BACKEND_URL}/api/linkedin/callback/"
# Basic LinkedIn scopes - organization scopes commented out until approved by LinkedIn
LINKEDIN_SCOPES = "openid,profile,email,w_member_social"  # ,rw_organization_admin,w_organization_social,r_organization_social,w_organization_social_feed,r_organization_social_feed
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, int(REDIS_PORT))],
            }
        }
    }

CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

CELERY_BEAT_SCHEDULE = {
    'check-scheduled-posts': {
        'task': 'apps.social_media.tasks.check_and_publish_scheduled_posts',
        'schedule': 60.0,  # Run every 60 seconds (1 minute)
        'options': {'expires': 59}  # Expire task if not executed within 59 seconds
    },
}

# Security Logging Configuration
import os

# Ensure logs directory exists with proper permissions
LOG_DIR = os.path.join(BASE_DIR, 'logs')
try:
    os.makedirs(LOG_DIR, exist_ok=True)
    # Create the security log file if it doesn't exist
    security_log_file = os.path.join(LOG_DIR, 'security.log')
    if not os.path.exists(security_log_file):
        open(security_log_file, 'a').close()
        os.chmod(security_log_file, 0o666)  # Make it writable
except (OSError, PermissionError):
    # If we can't create the log directory, use console logging only
    LOG_DIR = None

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Add file handler only if we can write to the logs directory
if LOG_DIR and os.access(LOG_DIR, os.W_OK):
    LOGGING['handlers']['security_file'] = {
        'level': 'WARNING',
        'class': 'logging.FileHandler',
        'filename': os.path.join(LOG_DIR, 'security.log'),
        'formatter': 'verbose',
    }
    LOGGING['loggers']['security']['handlers'].append('security_file')
    LOGGING['loggers']['django.security']['handlers'].append('security_file')

# Additional Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# JWT Cookie Security Settings
JWT_COOKIE_SECURE = not DEBUG  # Use secure cookies in production
JWT_COOKIE_HTTPONLY = True
JWT_COOKIE_SAMESITE = 'Lax'
JWT_COOKIE_MAX_AGE = 90 * 60  # 90 minutes (match ACCESS_TOKEN_LIFETIME)

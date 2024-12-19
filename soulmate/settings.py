
from pathlib import Path
from datetime import timedelta
import os
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-rbfn)$l@1cjd($rf75ycg_a$sc#shudp(xtpj1)q)=i=ox-z77'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

TWO_FACTOR_API_KEY = '15b274f8-8600-11ef-8b17-0200cd936042'
AGORA_APP_ID = '9626e8b5f847e6961cb9a996e1ae93'
AGORA_APP_CERTIFICATE = 'ab41eb854807425faa1b44481ff97fe3'


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'user',
    'rest_framework',
    'executive',
    'channels',
    'corsheaders',
    'django_celery_results',
    'django_celery_beat',
    'background_task',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',


]


# Celery Configuration
CELERY_BROKER_URL = 'rediss://:u9aa62geIAVPyoQvsDMFaNPO0eNdIAT6@redis-18183.c330.asia-south1-1.gce.redns.redis-cloud.com:18183/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'


# Celery Results Backend
CELERY_RESULT_BACKEND = 'django-db'  # Store task results in database
CELERY_CACHE_BACKEND = 'django-cache'  # Optional: use cache for storing states


ROOT_URLCONF = 'soulmate.urls'

ZEGOCLOUD_API = {
    'APP_ID': '574557540',
    'APP_SIGN': 'd1d01da09192718835de44163b28bfc8efb10205ba87262091a58b8bfada747d',
    'SERVER_SECRET': '7305340662eba47812cced6799f929e5',
    'CALLBACK_SECRET': 'd1d01da09192718835de44163b28bfc8',
    'SERVER_URL': 'wss://webliveroom574557540-api.coolzcloud.com/ws'
}

AUTH_USER_MODEL = 'executive.Admins'
AUTH_USER_MODEL = 'user.User'


AUTHENTICATION_BACKENDS = [
    'executive.authentication.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'soulmate.wsgi.application'

RAZORPAY_KEY_ID = 'your_key_id'
RAZORPAY_KEY_SECRET = 'your_key_secret'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'soulmate$def',  # Your database name (replace with your actual DB name)
        'USER': 'database-1',
        'PASSWORD': 'admin123',  # Replace with your actual MySQL password
        'HOST': 'database-1.cp86aus24g28.ap-south-1.rds.amazonaws.com',  # Your RDS endpoint
        'PORT': '3306',  # MySQL default port
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"
        }
    }
}





ZIGOCLOUD_API = {
    'APP_ID': 574557540,
    'API_KEY': 'd1d01da09192718835de44163b28bfc8efb10205ba87262091a58b8bfada747d',
    # Add other settings if needed
}
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'soulmate$database',  # Your database name (replace with your actual DB name)
#         'USER': 'soulmate',  # Your MySQL username
#         'PASSWORD': 'admin@123',  # Replace with your actual MySQL password
#         'HOST': 'soulmate.mysql.pythonanywhere-services.com',  # Your MySQL host address
#         'PORT': '3306',  # MySQL default port
#     }
# }


CORS_ALLOW_ALL_ORIGINS = True  # Allow all origins (for development purposes)
# You can restrict this by specifying allowed origins like below:
# CORS_ALLOWED_ORIGINS = [
#     'http://localhost:3000',
#     'http://127.0.0.1:3000',
# ]

CORS_ALLOW_CREDENTIALS = True

# Email backend (For OTP verification)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'praveen.codeedex@gmail.com'  # Replace with your email
EMAIL_HOST_PASSWORD = 'fbmq ueku gkav mygc'

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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

STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

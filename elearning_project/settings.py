import os
from dotenv import load_dotenv # Import load_dotenv
from pathlib import Path
# ... (BASE_DIR is already defined)




# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(os.path.join(BASE_DIR, '.env')) # Correct path to .env

# OpenAI API Key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'crispy_forms',
    'crispy_bootstrap5',

    # Local apps
    'core',      # Or just 'core'
    'users',    # Or just 'users'
    'courses',
    'forum',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'elearning_project.urls'

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
WSGI_APPLICATION = 'elearning_project.wsgi.application'
# elearning_project/settings.py

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

AUTH_USER_MODEL = 'users.CustomUser'
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')] # For project-level static files
# STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_collected') # For production deployment, not needed now

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# elearning_project/settings.py

LOGIN_REDIRECT_URL = 'users:student_dashboard'  # Where to redirect after successful login
LOGIN_URL = 'users:login'          # The URL name for the login page

LOGOUT_REDIRECT_URL = 'users:logged_out' # Or 'core:home'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS ='True' == 'True'
EMAIL_HOST_USER = 'abebefetene2@gmail.com'
EMAIL_HOST_PASSWORD ='zjuq qbqf eqci ossc'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER
SITE_DOMAIN = 'http://127.0.0.1:8000'
EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS = 24
OPENAI_CHAT_MODEL = "gpt-4o-mini" # Or your preferred model
OPENAI_CHAT_TEMPERATURE = 0.7
CHATBOT_MAX_HISTORY_LENGTH = 10
# GAMIFICATION SETTINGS
# Levels: (level_name, points_required_to_reach, optional_icon_class)
# The order matters: from lowest to highest points.
# The points_required is the minimum to be AT that level.
LEARNING_LEVELS = [
    {'name': 'Novice', 'points': 0, 'icon': 'bi-person-fill'},
    {'name': 'Apprentice', 'points': 100, 'icon': 'bi-person-workspace'},
    {'name': 'Journeyman', 'points': 250, 'icon': 'bi-tools'},
    {'name': 'Adept', 'points': 500, 'icon': 'bi-lightbulb-fill'},
    {'name': 'Expert', 'points': 1000, 'icon': 'bi-star-fill'},
    {'name': 'Master', 'points': 2000, 'icon': 'bi-trophy-fill'},
    {'name': 'Grandmaster', 'points': 5000, 'icon': 'bi-gem'},
]
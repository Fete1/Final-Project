import os
from dotenv import load_dotenv
from pathlib import Path

 # Import for database configuration
import dj_database_url
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file ONLY in local development.
# In Render, environment variables are set directly in the dashboard/render.yaml.
# Check for a specific environment variable that Render sets, or rely on DEBUG status.
# For local dev, ensure .env is in the same directory as manage.py (BASE_DIR)
dotenv_path = BASE_DIR / '.env'
if os.path.exists(dotenv_path) and os.environ.get('RENDER') is None: # Only load .env if not on Render
    print("Loading .env file for local development...")
    load_dotenv(dotenv_path)

# --- Core Settings ---
# SECRET_KEY: Get from environment variable. Generate a strong one for production.
# The default is ONLY for local dev if the env var isn't set.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'local_dev_unsafe_secret_key_replace_me_if_no_env')

# DEBUG: Controlled by environment variable. Default to False for safety.
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = []
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Add your custom domain(s) here if you have them
# Example: ALLOWED_HOSTS.extend(['www.yourdomain.com', 'yourdomain.com'])
# For local development:
if DEBUG:
    ALLOWED_HOSTS.extend(['localhost', '127.0.0.1'])


# --- Application definition ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic', # For serving static files with runserver in dev if needed (place before staticfiles)
    'django.contrib.staticfiles',

    # Third-party apps
    'crispy_forms',
    'crispy_bootstrap5',
    'storages', # For S3 or other cloud storage (if using for media)

    # Local apps
    'core.apps.CoreConfig', # Using AppConfig for clarity
    'users.apps.UsersConfig',
    'courses.apps.CoursesConfig',
    'forum.apps.ForumConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Whitenoise middleware - place early
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
        'DIRS': [BASE_DIR / 'templates'], 
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


# --- Crispy Forms ---
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


# --- Database ---
# Uses dj_database_url to parse DATABASE_URL from environment variable (provided by Render)
# Falls back to SQLite for local development if DATABASE_URL is not set.
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600, # Optional: Number of seconds database connections should persist
        conn_health_checks=True, # Optional: Enable health checks on the connection
    )
}
# Ensure SSL is required for PostgreSQL connections in production
if DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql' and not DEBUG:
    DATABASES['default']['OPTIONS'] = DATABASES['default'].get('OPTIONS', {})
    DATABASES['default']['OPTIONS']['sslmode'] = 'require'


# --- Password validation ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# --- Internationalization ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# --- Custom User Model ---
AUTH_USER_MODEL = 'users.CustomUser'


# --- Static files (CSS, JavaScript, Images) ---
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
# STATIC_ROOT is where collectstatic will gather all static files for deployment.
STATIC_ROOT = BASE_DIR / 'staticfiles_collected'
# Whitenoise storage backend for compression and manifest support
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# --- Media files (User Uploads) ---
# For production, use cloud storage (e.g., AWS S3).
# These AWS settings will be populated by environment variables on Render.
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME') # e.g., 'us-east-1'
AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL') # For S3-compatible services like DigitalOcean Spaces
AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_S3_CUSTOM_DOMAIN') # If using CloudFront or custom domain for S3
AWS_S3_FILE_OVERWRITE = False # Default: Do not overwrite files with the same name
AWS_DEFAULT_ACL = None # Default: Private. Set to 'public-read' if media should be public by default.
AWS_QUERYSTRING_AUTH = True # Default: Generate signed URLs for private files. Set False if using public-read ACL and no signed URLs.
AWS_LOCATION = 'media' # Optional: Subfolder in your S3 bucket for media files

if AWS_STORAGE_BUCKET_NAME and not DEBUG: # Use S3 only if bucket name is set and not in DEBUG
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    # MEDIA_URL will be constructed by S3Boto3Storage if AWS_S3_CUSTOM_DOMAIN is not set.
    # If you have a custom domain or CloudFront for S3 media:
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/'
    else: # Standard S3 URL structure
        MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{AWS_LOCATION}/'
    # MEDIA_ROOT is not used by S3 storage but Django might require it to be defined.
    MEDIA_ROOT = AWS_LOCATION # Or some dummy path, as files are not stored locally with S3
else: # Local development settings for media
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'


# --- Default primary key field type ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --- Authentication ---
LOGIN_REDIRECT_URL = 'users:student_dashboard'
LOGIN_URL = 'users:login'
LOGOUT_REDIRECT_URL = 'core:home' # Redirect to landing page after logout


# --- Email Configuration ---
# For production, use a transactional email service (SendGrid, Mailgun, Postmark, AWS SES)
# or ensure your Gmail setup is robust (less recommended for high volume).
# The following uses environment variables for sensitive email credentials.
EMAIL_BACKEND = os.environ.get('DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend') # Console for dev if not set
EMAIL_HOST = os.environ.get('DJANGO_EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('DJANGO_EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('DJANGO_EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('DJANGO_EMAIL_HOST_USER') # Your abebefetene2@gmail.com
EMAIL_HOST_PASSWORD = os.environ.get('DJANGO_EMAIL_HOST_PASSWORD') # Your Gmail App Password 'zjuq qbqf eqci ossc'
DEFAULT_FROM_EMAIL = os.environ.get('DJANGO_DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'webmaster@localhost')
SERVER_EMAIL = os.environ.get('DJANGO_SERVER_EMAIL', DEFAULT_FROM_EMAIL) # For error emails to admins

# --- Site and Verification Settings ---
SITE_DOMAIN = os.environ.get('SITE_DOMAIN', 'http://127.0.0.1:8000') # Important for email links
EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS = int(os.environ.get('EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS', 24))


# --- OpenAI API Settings ---
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
OPENAI_CHAT_MODEL = os.environ.get('OPENAI_CHAT_MODEL', "gpt-4o-mini")
OPENAI_CHAT_TEMPERATURE = float(os.environ.get('OPENAI_CHAT_TEMPERATURE', 0.7))
CHATBOT_MAX_HISTORY_LENGTH = int(os.environ.get('CHATBOT_MAX_HISTORY_LENGTH', 10))
EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', "text-embedding-ada-002") # From your ai_utils


# --- Gamification Settings ---
SAQ_MIN_LENGTH = int(os.environ.get('SAQ_MIN_LENGTH', 15))
LEARNING_LEVELS = [
    {'name': 'Novice', 'points': 0, 'icon': 'bi-person-fill'},
    {'name': 'Apprentice', 'points': 100, 'icon': 'bi-person-workspace'},
    {'name': 'Journeyman', 'points': 250, 'icon': 'bi-tools'},
    {'name': 'Adept', 'points': 500, 'icon': 'bi-lightbulb-fill'},
    {'name': 'Expert', 'points': 1000, 'icon': 'bi-star-fill'},
    {'name': 'Master', 'points': 2000, 'icon': 'bi-trophy-fill'},
    {'name': 'Grandmaster', 'points': 5000, 'icon': 'bi-gem'},
] # This can also be loaded from JSON in environment variable if it gets complex

# --- Production Security Settings ---
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') # If behind a proxy like Render's load balancer
    # SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin" # Django 4.0+
    SECURE_BROWSER_XSS_FILTER = True # Deprecated in some browsers, but good to have
    X_FRAME_OPTIONS = 'DENY'
    SECURE_CONTENT_TYPE_NOSNIFF = True

# --- Logging Configuration (Optional, but good for production) ---
# Example:
# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'handlers': {
#         'console': {
#             'class': 'logging.StreamHandler',
#         },
#     },
#     'root': {
#         'handlers': ['console'],
#         'level': 'INFO', # Change to WARNING for less verbosity in prod
#     },
#     'loggers': {
#         'django': {
#             'handlers': ['console'],
#             'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'), # Control Django's verbosity
#             'propagate': False,
#         },
#     },
# }
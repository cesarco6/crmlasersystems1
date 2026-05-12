"""
Django settings for config project.
"""
import os
from pathlib import Path
import sys

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# AÑADE ESTA LÍNEA: Permite que Django encuentre 'users' y 'leads'
sys.path.insert(0, os.path.join(BASE_DIR))

# --- SEGURIDAD Y ENTORNO ---
# Lee la llave segura desde tu archivo .env
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-default-key')

# Convierte el string 'True' o 'False' del .env a un booleano real
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# Lee los hosts permitidos del .env de forma segura
allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost')
ALLOWED_HOSTS = allowed_hosts_env.split(',')

# Orígenes de confianza para evitar errores de CSRF
CSRF_TRUSTED_ORIGINS = [
    'https://crm-ls.lat',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# Esencial para cuando Django corre detrás de un Proxy inverso (Nginx, Cloudflare) bajo HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# --- APLICACIONES ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'users',
    'leads',
    'django_q', # Tareas en segundo plano
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'config.middleware.MaintenanceModeMiddleware', # <-- Mantenimiento movido aquí
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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
                'leads.context_processors.contador_alertas', # Contador personalizado
                'users.context_processors.global_settings_processor', # Fuente global
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# --- BASE DE DATOS ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'crm_ls'),
        'USER': os.environ.get('POSTGRES_USER', 'crm_user'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'crm_password'),
        'HOST': os.environ.get('POSTGRES_HOST', 'db'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# --- INTERNACIONALIZACIÓN ---
LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

# --- ARCHIVOS ESTÁTICOS Y MEDIA ---
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login'

# --- AUTENTICACIÓN DUAL ---
AUTHENTICATION_BACKENDS = [
    'users.backends.EmailAuthBackend',          # 1. Custom Scanner (por Email)
    'django.contrib.auth.backends.ModelBackend',# 2. Fallback nativo (por Username)
]

# --- CONFIGURACIÓN DE DJANGO Q (TAREAS EN SEGUNDO PLANO) ---
Q_CLUSTER = {
    'name': 'crm_laser_cluster',
    'workers': 4,
    'recycle': 500,
    'timeout': 60,
    'compress': True,
    'save_limit': 250,
    'queue_limit': 500,
    'cpu_affinity': 1,
    'label': 'Django Q',
    'redis': os.environ.get('REDIS_URL', 'redis://redis:6379/1') # Lee de tu .env correctamente
}

"""
Django settings for proyectoDesarrollo project.

Generated by 'django-admin startproject' using Django 5.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import os  # <-- ¡Importante agregar esta línea!

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-5bluxl5na1#wnt1576=xcs&#55w!p6l4#_-m1sjyfku2fa00v='

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True  # Ponlo False en producción

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '35.222.2.211',
    'desarrollo.smartgest.cl'
        # Ajusta con tu IP o dominio
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Terceros
    'rest_framework',
    'corsheaders',  # <-- Asegúrate de tenerlo instalado y aquí
    # Tus apps
    'coreempresas',
    'configuracion',
    'operadores',
    'tasks',
    'logs',
    # etc...
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # <-- Importante que vaya antes de CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'proyectoDesarrollo.urls'

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

WSGI_APPLICATION = 'proyectoDesarrollo.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mi_basedatos',      
        'USER': 'mi_usuario',        
        'PASSWORD': 'mi_password',   
        'HOST': 'localhost',         
        'PORT': '5432',              
    }
}

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ============================================
# CORS CONFIGURATION PARA INCLUIR CREDENCIALES
# ============================================
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',      
    'http://35.222.2.211:8000',
    'http://0.0.0.0:5173',    
    'http://0.0.0.0:8000',    
]
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173',
    'http://35.222.2.211:8000',
    'http://0.0.0.0:5173',
    'http://0.0.0.0:8000',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        # etc...
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
}

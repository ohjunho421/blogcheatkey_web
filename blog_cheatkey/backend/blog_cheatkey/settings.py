import os
import sys
import jwt
from pathlib import Path
from dotenv import load_dotenv

# backend 폴더를 파이썬 경로에 추가하여, 앱들을 간단한 라벨로 사용할 수 있게 함
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# .env 파일 로드
load_dotenv()

# BASE_DIR 설정: 프로젝트의 루트 경로 (manage.py가 위치한 폴더의 부모)
BASE_DIR = Path(__file__).resolve().parent.parent

# 보안 및 디버그 설정
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-your-secret-key-here')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

# 커스텀 사용자 모델 설정: 앱 내부에서 기본 라벨은 "accounts" (AppConfig가 따로 지정되지 않았다면)
AUTH_USER_MODEL = 'accounts.User'

# 프론트엔드 URL 설정
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# 데이터베이스 설정 (SQLite 예시)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# 캐시 설정 추가
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# API 키 설정 (필요에 따라 .env 파일에 설정)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
PERPLEXITY_API_KEY = os.environ.get('PERPLEXITY_API_KEY','')


# Application definition
INSTALLED_APPS = [
    # Django 기본 앱
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 제3자 앱
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'allauth',       
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.kakao',
    'allauth.socialaccount.providers.naver',

    # 프로젝트 앱 (backend 폴더 하위에 위치한 앱들; 폴더 이름이 앱 라벨로 사용됨)
    'accounts',
    'core',
    'key_word',
    'research',
    'content',
    'title',
    'history',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # CORS 미들웨어
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # allauth 관련 미들웨어
]

ROOT_URLCONF = 'blog_cheatkey.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'frontend/build')],
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

# django-allauth 관련 설정 추가
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# 소셜 계정 설정
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
            'secret': os.environ.get('GOOGLE_CLIENT_SECRET', ''),
            'key': ''
        },
        'SCOPE': ['profile', 'email'],
    },
    'facebook': {
        'APP': {
            'client_id': os.environ.get('FACEBOOK_CLIENT_ID', ''),
            'secret': os.environ.get('FACEBOOK_CLIENT_SECRET', ''),
            'key': ''
        },
        'SCOPE': ['email', 'public_profile'],
    },
    'kakao': {
        'APP': {
            'client_id': os.environ.get('KAKAO_CLIENT_ID', ''),
            'secret': os.environ.get('KAKAO_CLIENT_SECRET', ''),
            'key': ''
        },
    },
    'naver': {
        'APP': {
            'client_id': os.environ.get('NAVER_CLIENT_ID', ''),
            'secret': os.environ.get('NAVER_CLIENT_SECRET', ''),
            'key': ''
        },
    }
}

# 로그인 성공 후 리디렉션 URL
LOGIN_REDIRECT_URL = '/'

# 소셜 계정 로그인 후 사용자 정보를 자동으로 업데이트
SOCIALACCOUNT_STORE_TOKENS = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'

WSGI_APPLICATION = 'blog_cheatkey.wsgi.application'

# REST Framework 설정
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

# CORS 설정
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
CORS_ALLOW_CREDENTIALS = True

# 개발 환경에서만 모든 출처 허용
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True

# 정적 파일 설정
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'frontend/build/static'),  # React 빌드 정적 파일 경로
]

# CSRF 설정
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://localhost:3000').split(',')
CSRF_COOKIE_SAMESITE = 'Lax'  # 또는 'None' (하지만 'None'인 경우 SECURE_COOKIE가 True여야 함)
CSRF_COOKIE_HTTPONLY = False  # JavaScript에서 접근 가능하도록 설정
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'False') == 'True'  # HTTPS 사용 시 True로 설정

# 미디어 파일 설정
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DEFAULT_TIMEOUT = 300  # 5분 (300초)

if DEBUG:
    print(f"MEDIA_ROOT 경로: {MEDIA_ROOT}")
    print(f"MEDIA_URL: {MEDIA_URL}")
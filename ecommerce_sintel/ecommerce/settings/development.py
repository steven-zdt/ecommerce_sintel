import os
from .base import *

DEBUG = True
CORS_ALLOW_ALL_ORIGINS = True

# Cache: ver switch CACHE_BACKEND (redis|locmem) en base.py

# DB: PostgreSQL en Docker (DB_HOST definido), SQLite en local sin Docker
if os.getenv('DB_HOST'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST'),
            'PORT': config('DB_PORT', default=5432, cast=int),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

DJANGO_VITE['default']['dev_mode'] = True

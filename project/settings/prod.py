"""Production settings."""

from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ["stockedge.example.com"]
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

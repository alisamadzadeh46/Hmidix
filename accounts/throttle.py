"""Brute-force protection for the login form.

Failed attempts are counted per phone number in Django's cache. After
``LOGIN_MAX_ATTEMPTS`` failures the number is locked for
``LOGIN_LOCKOUT_SECONDS``; a successful login clears the counter.

The key is the phone number rather than the client IP because the site runs
behind a CDN, where every visitor can appear to share a handful of IPs.
"""
from django.conf import settings
from django.core.cache import cache

KEY_PREFIX = 'login-failures:'


def _key(phone):
    return f'{KEY_PREFIX}{phone}'


def is_locked(phone):
    """Return True if too many failed logins were recorded for ``phone``."""
    return cache.get(_key(phone), 0) >= settings.LOGIN_MAX_ATTEMPTS


def register_failure(phone):
    """Record one failed login; the window restarts with every failure."""
    key = _key(phone)
    cache.set(key, cache.get(key, 0) + 1, settings.LOGIN_LOCKOUT_SECONDS)


def reset(phone):
    """Forget previous failures after a successful login."""
    cache.delete(_key(phone))

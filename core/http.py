"""Small HTTP helpers used across views."""
from django.shortcuts import resolve_url
from django.utils.http import url_has_allowed_host_and_scheme


def safe_redirect_url(request, url, fallback):
    """Return ``url`` if it points to this site, otherwise ``fallback``.

    Guards every user-supplied redirect target (``?next=``, the Referer header)
    against open-redirect attacks. ``fallback`` may be a URL, a URL pattern
    name or a model instance, exactly like ``django.shortcuts.redirect``.
    """
    if url and url_has_allowed_host_and_scheme(
        url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return url
    return resolve_url(fallback)


def referer_or(request, fallback):
    """Return the safe Referer URL of the request, or ``fallback``."""
    return safe_redirect_url(request, request.META.get('HTTP_REFERER'), fallback)


def parse_int(value, default=0, minimum=None):
    """Parse ``value`` as an int, returning ``default`` for invalid input.

    When ``minimum`` is given, the result is clamped to be at least that value.
    """
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    if minimum is not None:
        number = max(number, minimum)
    return number

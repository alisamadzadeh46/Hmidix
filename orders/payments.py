"""Payment gateway loading.

The concrete gateway implementation lives in its own module, configured with
the ``PAYMENT_GATEWAY`` setting (a dotted module path). Keeping the views
decoupled from any one provider means a new gateway can be added by writing a
module with the functions below and pointing the setting at it.

A gateway module must provide::

    payment_request(amount, description, callback_url, mobile=None, email=None)
        -> (authority: str | None, error: str | None)

    payment_verify(amount, authority)
        -> (ref_id: int | None, error: str | None)

    gateway_url(authority) -> str
        URL the customer is redirected to in order to pay.
"""
from functools import lru_cache
from importlib import import_module

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

REQUIRED_FUNCTIONS = ('payment_request', 'payment_verify', 'gateway_url')


@lru_cache(maxsize=None)
def _load(module_path):
    try:
        module = import_module(module_path)
    except ImportError as exc:
        raise ImproperlyConfigured(
            f'Payment gateway module "{module_path}" could not be imported.'
        ) from exc
    missing = [name for name in REQUIRED_FUNCTIONS if not callable(getattr(module, name, None))]
    if missing:
        raise ImproperlyConfigured(
            f'Payment gateway "{module_path}" is missing: {", ".join(missing)}.'
        )
    return module


def get_gateway():
    """Return the configured payment gateway module."""
    return _load(settings.PAYMENT_GATEWAY)

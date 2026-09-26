from django.conf import settings

from .models import Category


def navigation(request):
    """Expose active categories to every template (for the main nav)."""
    return {
        'nav_categories': Category.objects.filter(is_active=True),
    }


def store_info(request):
    """Expose deployment-specific store details to every template.

    Contact channels and the e-Namad seal are configured through environment
    variables (see ``STORE_CONTACT`` and ``ENAMAD_*`` in settings); templates
    only render the entries that have a value.
    """
    enamad = None
    if settings.ENAMAD_ID and settings.ENAMAD_CODE:
        enamad = {'id': settings.ENAMAD_ID, 'code': settings.ENAMAD_CODE}
    return {
        'store': settings.STORE_CONTACT,
        'enamad': enamad,
    }

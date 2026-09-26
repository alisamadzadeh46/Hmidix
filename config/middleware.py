"""Security response headers.

Django ships settings for a few of these (HSTS, nosniff, referrer policy), but
the modern isolation/permission headers have no built-in setting, so we add
them here. Kept in one place so the policy is easy to audit and adjust.
"""


class SecurityHeadersMiddleware:
    """Attach hardening headers to every response."""

    # Inline scripts/styles are used throughout the templates, so 'unsafe-inline'
    # is required for now. Images come from our own media plus the e-Namad seal.
    CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https://trustseal.enamad.ir; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "object-src 'none'"
    )

    HEADERS = {
        'Content-Security-Policy': CSP,
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=(), payment=()',
        'X-Permitted-Cross-Domain-Policies': 'none',
        'Cross-Origin-Opener-Policy': 'same-origin',
        'Cross-Origin-Resource-Policy': 'same-origin',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        for header, value in self.HEADERS.items():
            response.setdefault(header, value)
        return response

"""In-memory payment gateway used by the test suite (see orders/payments.py)."""

VERIFIED = {}


def payment_request(amount, description, callback_url, mobile=None, email=None):
    return 'AUTH-1', None


def payment_verify(amount, authority):
    if authority != 'AUTH-1':
        return None, 'invalid authority'
    VERIFIED[authority] = amount
    return 123456, None


def gateway_url(authority):
    return f'https://gateway.example/pay/{authority}'

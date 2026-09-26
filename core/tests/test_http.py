from django.test import RequestFactory, SimpleTestCase

from core.http import parse_int, safe_redirect_url


class SafeRedirectUrlTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get('/')

    def test_keeps_local_path(self):
        self.assertEqual(safe_redirect_url(self.request, '/cart/', '/'), '/cart/')

    def test_rejects_external_and_protocol_relative_urls(self):
        for url in ('https://evil.example/', '//evil.example/', 'javascript:alert(1)'):
            with self.subTest(url=url):
                self.assertEqual(safe_redirect_url(self.request, url, '/home/'), '/home/')

    def test_empty_url_uses_fallback(self):
        self.assertEqual(safe_redirect_url(self.request, '', '/home/'), '/home/')


class ParseIntTests(SimpleTestCase):
    def test_parses_valid_number(self):
        self.assertEqual(parse_int('3'), 3)

    def test_invalid_input_returns_default(self):
        self.assertEqual(parse_int('abc', default=1), 1)
        self.assertEqual(parse_int(None, default=1), 1)

    def test_minimum_is_applied(self):
        self.assertEqual(parse_int('-5', minimum=1), 1)

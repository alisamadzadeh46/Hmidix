from django.test import TestCase
from django.urls import reverse

from .factories import make_product

STATIC_PAGES = ['shop:home', 'shop:about', 'shop:contact', 'shop:how_to_order',
                'shop:shipping', 'shop:payment_methods', 'shop:product_list']


class PageRenderTests(TestCase):
    def test_static_pages_render(self):
        for name in STATIC_PAGES:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_product_detail_renders(self):
        product = make_product()
        self.assertEqual(self.client.get(product.get_absolute_url()).status_code, 200)

    def test_store_details_are_hidden_when_not_configured(self):
        with self.settings(STORE_CONTACT={}, ENAMAD_ID='', ENAMAD_CODE=''):
            html = self.client.get(reverse('shop:contact')).content.decode()
        self.assertNotIn('tel:', html)
        self.assertNotIn('trustseal.enamad.ir/logo', html)

    def test_store_details_are_rendered_when_configured(self):
        contact = {'phone': '09121112233', 'telegram_support': 'shop_support'}
        with self.settings(STORE_CONTACT=contact, ENAMAD_ID='1', ENAMAD_CODE='abc'):
            html = self.client.get(reverse('shop:contact')).content.decode()
        self.assertIn('tel:09121112233', html)
        self.assertIn('https://t.me/shop_support', html)
        self.assertIn('trustseal.enamad.ir/logo.aspx?id=1&Code=abc', html)

    def test_review_requires_login(self):
        product = make_product()
        response = self.client.post(reverse('shop:add_review', args=[product.slug]),
                                    {'rating': 5, 'text': 'Good'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('accounts:login')))

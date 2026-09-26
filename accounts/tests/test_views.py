from django.test import TestCase
from django.urls import reverse

from shop.tests.factories import make_user


class LoginTests(TestCase):
    def setUp(self):
        make_user(phone='09120000001', password='secret123')
        self.url = reverse('accounts:login')

    def login(self, next_url):
        return self.client.post(f'{self.url}?next={next_url}', {
            'action': 'login', 'phone': '09120000001', 'password': 'secret123',
        })

    def test_login_redirects_to_local_next(self):
        self.assertRedirects(self.login('/cart/'), '/cart/', fetch_redirect_response=False)

    def test_login_ignores_external_next(self):
        response = self.login('https://evil.example/')
        self.assertRedirects(response, reverse('shop:home'), fetch_redirect_response=False)

    def test_wrong_password_is_rejected(self):
        response = self.client.post(self.url, {
            'action': 'login', 'phone': '09120000001', 'password': 'wrong',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)


class AddressAccessTests(TestCase):
    def test_user_cannot_edit_someone_elses_address(self):
        owner = make_user(phone='09120000001')
        address = owner.addresses.create(
            title='Home', receiver='Owner', phone='09120000001',
            province='P', city='C', address='Street 1',
        )
        self.client.force_login(make_user(phone='09120000002'))
        url = reverse('accounts:address_edit', args=[address.pk])
        self.assertEqual(self.client.get(url).status_code, 404)


class LogoutTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user())
        self.url = reverse('accounts:logout')

    def test_get_does_not_log_out(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

    def test_post_logs_out(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('shop:home'), fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)

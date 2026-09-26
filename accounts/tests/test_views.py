from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
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


class RegisterTests(TestCase):
    def register(self, password):
        return self.client.post(reverse('accounts:login'), {
            'action': 'register', 'full_name': 'New User', 'phone': '09120000009',
            'email': 'new@example.com', 'password': password,
        })

    def test_common_password_is_rejected(self):
        self.register('123456')
        self.assertFalse(get_user_model().objects.filter(phone='09120000009').exists())

    def test_valid_registration_logs_user_in(self):
        self.register('a-Strong-pass-42')
        self.assertTrue(get_user_model().objects.filter(phone='09120000009').exists())
        self.assertIn('_auth_user_id', self.client.session)


@override_settings(LOGIN_MAX_ATTEMPTS=3)
class LoginThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        make_user(phone='09120000001', password='secret123')
        self.url = reverse('accounts:login')

    def attempt(self, password):
        self.client.post(self.url, {
            'action': 'login', 'phone': '09120000001', 'password': password,
        })
        return '_auth_user_id' in self.client.session

    def test_phone_is_locked_after_repeated_failures(self):
        for _ in range(3):
            self.assertFalse(self.attempt('wrong'))
        # Even the correct password is refused while the lock is active.
        self.assertFalse(self.attempt('secret123'))

    def test_successful_login_resets_counter(self):
        self.attempt('wrong')
        self.attempt('wrong')
        self.assertTrue(self.attempt('secret123'))
        self.client.logout()
        self.attempt('wrong')
        self.assertTrue(self.attempt('secret123'))

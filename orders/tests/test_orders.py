from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from orders.models import Coupon, Order
from shop.models import Product
from shop.tests.factories import make_product, make_user


class CouponTests(TestCase):
    def test_percent_discount(self):
        coupon = Coupon(code='OFF10', discount_type=Coupon.TYPE_PERCENT, value=10)
        self.assertEqual(coupon.discount_amount(1000), 100)

    def test_fixed_discount_never_exceeds_amount(self):
        coupon = Coupon(code='FIX', discount_type=Coupon.TYPE_FIXED, value=5000)
        self.assertEqual(coupon.discount_amount(1000), 1000)

    def test_minimum_amount_is_enforced(self):
        coupon = Coupon(code='MIN', value=10, min_amount=500)
        ok, error = coupon.validate_for(100)
        self.assertFalse(ok)
        self.assertTrue(error)

    def test_code_is_normalised_on_save(self):
        coupon = Coupon.objects.create(code='  summer ', value=10)
        self.assertEqual(coupon.code, 'SUMMER')


class CartTests(TestCase):
    def test_add_with_invalid_quantity_falls_back_to_one(self):
        product = make_product()
        self.client.post(reverse('orders:cart_add', args=[product.pk]), {'quantity': 'x'})
        self.assertEqual(self.client.session['cart'], {str(product.pk): 1})

    def test_out_of_stock_product_cannot_be_added(self):
        product = make_product(stock=0)
        response = self.client.post(reverse('orders:cart_add', args=[product.pk]),
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.session.get('cart', {}), {})

    def test_quantity_is_capped_to_stock(self):
        product = make_product(stock=3)
        self.client.post(reverse('orders:cart_add', args=[product.pk]), {'quantity': 10})
        self.assertEqual(self.client.session['cart'], {str(product.pk): 3})

    def test_cart_shows_colleague_unit_price(self):
        product = make_product(price=1000, colleague_price=800)
        self.client.force_login(make_user(role=User.ROLE_COLLEAGUE))
        self.client.post(reverse('orders:cart_add', args=[product.pk]))
        html = self.client.get(reverse('orders:cart')).content.decode()
        self.assertIn('۸۰۰ ریال', html)
        self.assertNotIn('۱،۰۰۰ ریال', html)

    def test_call_for_price_product_cannot_be_added(self):
        product = make_product(call_for_price=True)
        self.client.post(reverse('orders:cart_add', args=[product.pk]))
        self.assertEqual(self.client.session.get('cart', {}), {})


@override_settings(PAYMENT_GATEWAY='orders.tests.fake_gateway')
class CheckoutAndPaymentTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product(price=1000)
        self.client.force_login(self.user)
        self.client.post(reverse('orders:cart_add', args=[self.product.pk]), {'quantity': 2})

    def checkout(self):
        return self.client.post(reverse('orders:checkout'), {
            'full_name': 'Customer', 'phone': '09120000001', 'address': 'Street 1',
        })

    def test_checkout_creates_order_and_redirects_to_payment(self):
        response = self.checkout()
        order = Order.objects.get()
        self.assertRedirects(response, reverse('orders:payment_start', args=[order.pk]),
                             fetch_redirect_response=False)
        self.assertEqual(order.total, 2000)
        self.assertEqual(order.items.get().quantity, 2)

    def test_coupon_usage_is_counted(self):
        coupon = Coupon.objects.create(code='OFF', value=10)
        self.client.post(reverse('orders:coupon_apply'), {'code': 'off'})
        self.checkout()
        coupon.refresh_from_db()
        self.assertEqual(coupon.used_count, 1)
        self.assertEqual(Order.objects.get().total, 1800)

    def test_full_payment_flow(self):
        self.checkout()
        order = Order.objects.get()
        response = self.client.get(reverse('orders:payment_start', args=[order.pk]))
        self.assertRedirects(response, 'https://gateway.example/pay/AUTH-1',
                             fetch_redirect_response=False)

        verify_url = reverse('orders:payment_verify', args=[order.pk])
        self.client.get(verify_url, {'Status': 'OK', 'Authority': 'AUTH-1'})
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_PAID)
        self.assertEqual(order.ref_id, 123456)

    def test_payment_deducts_stock_once(self):
        self.product.stock = 2
        self.product.save()
        self.checkout()
        order = Order.objects.get()
        self.client.get(reverse('orders:payment_start', args=[order.pk]))
        verify_url = reverse('orders:payment_verify', args=[order.pk])
        self.client.get(verify_url, {'Status': 'OK', 'Authority': 'AUTH-1'})
        self.client.get(verify_url, {'Status': 'OK', 'Authority': 'AUTH-1'})

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)
        self.assertEqual(self.product.status, Product.STATUS_OUT)

    def test_verify_rejects_authority_of_another_order(self):
        self.checkout()
        order = Order.objects.get()
        self.client.get(reverse('orders:payment_start', args=[order.pk]))
        self.client.get(reverse('orders:payment_verify', args=[order.pk]),
                        {'Status': 'OK', 'Authority': 'OTHER'})
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_PENDING)


class OrderAccessTests(TestCase):
    def setUp(self):
        owner = make_user(phone='09120000001')
        self.order = Order.objects.create(user=owner, full_name='Owner',
                                          phone='09120000001', address='Street 1')
        self.url = self.order.get_absolute_url()

    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('accounts:login')))

    def test_other_user_cannot_see_order(self):
        self.client.force_login(make_user(phone='09120000002'))
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_other_user_cannot_start_payment(self):
        self.client.force_login(make_user(phone='09120000002'))
        url = reverse('orders:payment_start', args=[self.order.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

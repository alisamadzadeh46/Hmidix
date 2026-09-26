from django.test import TestCase

from accounts.models import User
from shop.models import Product

from .factories import make_product, make_user


class ProductPriceTests(TestCase):
    def test_colleague_sees_colleague_price(self):
        product = make_product(price=100, colleague_price=80)
        colleague = make_user(role=User.ROLE_COLLEAGUE)
        self.assertEqual(product.price_for(colleague), 80)

    def test_normal_user_sees_normal_price(self):
        product = make_product(price=100, colleague_price=80)
        self.assertEqual(product.price_for(make_user()), 100)

    def test_out_of_stock_status_is_set_on_save(self):
        product = make_product(stock=0)
        self.assertEqual(product.status, Product.STATUS_OUT)
        self.assertFalse(product.in_stock)

    def test_discount_percent(self):
        self.assertEqual(make_product(price=75, old_price=100).discount_percent, 25)

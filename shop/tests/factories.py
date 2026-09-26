"""Minimal object builders shared by the test suites."""
from django.contrib.auth import get_user_model

from shop.models import Category, Product


def make_user(phone='09120000001', password='secret123', **extra):
    return get_user_model().objects.create_user(phone=phone, password=password, **extra)


def make_product(name='Camera', price=1_000_000, stock=10, **extra):
    category = extra.pop('category', None) or Category.objects.get_or_create(
        name='Cameras', slug='cameras')[0]
    return Product.objects.create(
        category=category, name=name, slug=extra.pop('slug', name.lower()),
        price=price, stock=stock, **extra,
    )

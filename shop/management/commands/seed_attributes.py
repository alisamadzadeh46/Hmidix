"""Seed a set of example product attributes (filters + specs) and attach
sensible example values to existing camera products so the dynamic filter /
spec features are visible out of the box.

Idempotent — safe to run repeatedly. Products that already have any attribute
values are left untouched, so it never overwrites real data.

    python manage.py seed_attributes
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils.text import slugify

from shop.models import Attribute, AttributeValue, Category, Product

# attribute name -> (unit, [values], show_in_specs, is_filterable)
ATTRIBUTES = [
    ('مگاپیکسل', 'مگاپیکسل', ['۲', '۳', '۴', '۵', '۸'], True, True),
    ('دید در شب', '', ['دارد', 'ندارد'], True, True),
    ('میکروفون', '', ['دارد', 'ندارد'], True, True),
    ('ضدآب (IP67)', '', ['دارد', 'ندارد'], True, True),
    ('نوع اتصال', '', ['تحت شبکه (IP)', 'آنالوگ', 'بی‌سیم (Wi-Fi)'], True, True),
]

# Attributes are attached to categories whose name matches any of these.
CAMERA_KEYWORDS = ['دوربین', 'dvr', 'nvr']


class Command(BaseCommand):
    help = 'ساخت ویژگی‌های نمونه و انتساب مقادیر نمونه به محصولات دوربین'

    def handle(self, *args, **options):
        cam_q = Q()
        for kw in CAMERA_KEYWORDS:
            cam_q |= Q(name__icontains=kw)
        cam_categories = list(Category.objects.filter(cam_q))

        created_attrs = 0
        attr_value_map = {}  # attribute name -> list[AttributeValue]

        for order, (name, unit, values, in_specs, filterable) in enumerate(ATTRIBUTES):
            attr, was_created = Attribute.objects.get_or_create(
                name=name,
                defaults={
                    'slug': slugify(name, allow_unicode=True),
                    'unit': unit,
                    'show_in_specs': in_specs,
                    'is_filterable': filterable,
                    'order': order,
                },
            )
            created_attrs += int(was_created)
            if cam_categories:
                attr.categories.add(*cam_categories)

            vals = []
            for v_order, val in enumerate(values):
                av, _ = AttributeValue.objects.get_or_create(
                    attribute=attr, value=val, defaults={'order': v_order})
                vals.append(av)
            attr_value_map[name] = vals

        self.stdout.write(self.style.SUCCESS(
            f'ویژگی‌ها آماده شد ({created_attrs} مورد جدید).'))

        # Assign example values to camera products that have none yet.
        if cam_categories:
            products = Product.objects.filter(category__in=cam_categories)
            mp_vals = attr_value_map['مگاپیکسل']
            nv_yes = attr_value_map['دید در شب'][0]
            mic_vals = attr_value_map['میکروفون']
            wp_vals = attr_value_map['ضدآب (IP67)']
            conn_vals = attr_value_map['نوع اتصال']
            assigned = 0
            for i, p in enumerate(products):
                if p.attribute_values.exists():
                    continue
                p.attribute_values.add(
                    mp_vals[i % len(mp_vals)],
                    nv_yes,
                    mic_vals[i % 2],
                    wp_vals[i % 2],
                    conn_vals[i % len(conn_vals)],
                )
                assigned += 1
            self.stdout.write(self.style.SUCCESS(
                f'مقادیر نمونه به {assigned} محصول اختصاص یافت.'))
        else:
            self.stdout.write(self.style.WARNING('دستهٔ دوربینی پیدا نشد.'))

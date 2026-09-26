"""Import the products that were previously hard-coded in the static HTML
pages into the database, and copy their images into MEDIA_ROOT.

Run once after migrating:  python manage.py seed_products
"""
import re
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from shop.models import Category, Product

# Source HTML page (relative to _legacy/) -> (category name, fa icon, nav order)
LEGACY_DIR = '_legacy'
PAGES = [
    ('analog_cam.html', 'دوربین مداربسته آنالوگ', 'fa-video', 1),
    ('net_cam.html', 'دوربین مداربسته تحت شبکه', 'fa-wifi', 2),
    ('DVR.html', 'دستگاه ضبط تصاویر DVR', 'fa-hdd', 3),
    ('NVR.html', 'دستگاه ضبط تصاویر NVR', 'fa-server', 4),
    ('Burglar_alarm.html', 'دزدگیر اماکن', 'fa-bell', 5),
    ('accessories_computer.html', 'لوازم جانبی کامپیوتر', 'fa-keyboard', 6),
]

CARD_RE = re.compile(r'<div class="product-card">(.*?)</div>\s*</div>', re.DOTALL)
IMG_RE = re.compile(r'<img\s+src="([^"]+)"', re.DOTALL)
TITLE_RE = re.compile(r'<h3 class="product-title">(.*?)</h3>', re.DOTALL)
PRICE_RE = re.compile(r'current-price">\s*([\d,]+)', re.DOTALL)


class Command(BaseCommand):
    help = 'Seed categories and products from the legacy static HTML pages.'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true',
                            help='Delete existing products/categories first.')

    def handle(self, *args, **options):
        base = Path(settings.BASE_DIR)
        static_dir = base / 'static'
        media_products = Path(settings.MEDIA_ROOT) / 'products'
        media_products.mkdir(parents=True, exist_ok=True)

        if options['flush']:
            Product.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write('Existing products and categories deleted.')

        total = 0
        for filename, cat_name, icon, order in PAGES:
            page = base / LEGACY_DIR / filename
            if not page.exists():
                self.stderr.write(f'پرونده یافت نشد: {filename}')
                continue

            category, _ = Category.objects.get_or_create(
                name=cat_name,
                defaults={'slug': slugify(cat_name, allow_unicode=True),
                          'icon': icon, 'order': order},
            )

            html = page.read_text(encoding='utf-8', errors='ignore')
            count = 0
            for block in CARD_RE.findall(html):
                title_m = TITLE_RE.search(block)
                price_m = PRICE_RE.search(block)
                if not title_m:
                    continue
                name = re.sub(r'\s+', ' ', title_m.group(1)).strip()
                if not name:
                    continue
                price = int(price_m.group(1).replace(',', '')) if price_m else 0

                # Derive model code from image filename when available
                img_m = IMG_RE.search(block)
                image_field = None
                model_code = ''
                if img_m:
                    src = img_m.group(1).lstrip('/')
                    src_path = static_dir / src
                    if src_path.exists():
                        model_code = src_path.stem
                        dest = media_products / src_path.name
                        if not dest.exists():
                            shutil.copy2(src_path, dest)
                        image_field = f'products/{src_path.name}'

                slug_base = (slugify(model_code or name, allow_unicode=True)[:270]
                             or slugify(name, allow_unicode=True)[:270])
                slug = slug_base
                i = 1
                while Product.objects.filter(slug=slug).exists():
                    i += 1
                    slug = f'{slug_base}-{i}'

                Product.objects.create(
                    category=category,
                    name=name,
                    slug=slug,
                    model_code=model_code,
                    image=image_field,
                    price=price,
                    stock=10,
                    is_featured=True,
                )
                count += 1
            total += count
            self.stdout.write(self.style.SUCCESS(
                f'{cat_name}: {count} محصول وارد شد.'))

        self.stdout.write(self.style.SUCCESS(f'مجموع {total} محصول ثبت شد.'))

"""Render a read-only, static copy of the storefront (e.g. for GitHub Pages).

The site is crawled with Django's test client starting from the home page;
every page reachable through a plain link is saved as ``<path>/index.html``.
Static and uploaded media files are copied next to it, and all URLs are
prefixed with ``--base-path`` so the copy works from a sub-directory such as
``https://<user>.github.io/<repo>/``.

Anything that needs the server (login, cart, checkout, filters) cannot work in
a static copy, so a small notice is added to every page and form submissions
are intercepted.

    python manage.py build_static_demo --output _site --base-path /Hmidix/
"""
import re
import shutil
from pathlib import Path
from urllib.parse import unquote, urldefrag

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.test import Client, override_settings
from django.urls import reverse, set_script_prefix

from shop.models import Banner, Product
from shop.views import CategoryView, ProductListView

HREF_RE = re.compile(r'href="([^"]+)"')

# Paths that are never exported: admin, per-user pages and POST-only endpoints.
SKIPPED_PREFIXES = ('hx-secure', 'auth/profile', 'auth/logout', 'cart/add', 'order/')

# Banners created by --demo-data (files from static/images).
DEMO_HERO_BANNERS = ['baner2.webp', 'baner3.webp']

DEMO_NOTICE = """
<div style="background:#1e293b;color:#fff;text-align:center;padding:10px 16px;font-size:13px;">
  این یک نسخه‌ی نمایشی ثابت از سایت است؛ ورود، سبد خرید، فیلترها و پرداخت در آن غیرفعال هستند.
</div>
<script>
  // Nothing can be submitted on a static host; explain instead of failing.
  document.addEventListener('submit', function (e) {
    e.preventDefault();
    alert('این بخش در نسخه‌ی نمایشی غیرفعال است.');
  }, true);
  document.addEventListener('click', function (e) {
    if (e.target.closest('.add-to-cart[data-add-url]')) {
      e.preventDefault();
      e.stopImmediatePropagation();
      alert('این بخش در نسخه‌ی نمایشی غیرفعال است.');
    }
  }, true);
</script>
"""


class Command(BaseCommand):
    help = 'Export a static, read-only copy of the storefront.'

    def add_arguments(self, parser):
        parser.add_argument('--output', default='_site', help='Output directory.')
        parser.add_argument('--base-path', default='/',
                            help='URL prefix the site is served under, e.g. /Hmidix/.')
        parser.add_argument('--demo-data', action='store_true',
                            help='Add demo banners and featured products first.')

    def handle(self, *args, **options):
        output = Path(options['output']).resolve()
        base = '/' + options['base_path'].strip('/') + '/'
        base = '/' if base == '//' else base

        if options['demo_data']:
            self._add_demo_data()

        if output.exists():
            shutil.rmtree(output)
        (output / 'static').mkdir(parents=True)

        overrides = {
            'DEBUG': False,
            'ALLOWED_HOSTS': ['testserver'],
            'FORCE_SCRIPT_NAME': base.rstrip('/') or None,
            'STATIC_URL': f'{base}static/',
            'MEDIA_URL': f'{base}media/',
            'STATIC_ROOT': output / 'static',
            'STORAGES': {
                **settings.STORAGES,
                'staticfiles': {
                    'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
                },
            },
        }
        with override_settings(**overrides):
            set_script_prefix(base)
            try:
                pages = self._crawl(base, output)
                self._write_404(output)
            finally:
                set_script_prefix('/')
            call_command('collectstatic', interactive=False, verbosity=0,
                         ignore_patterns=['admin'])

        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists():
            shutil.copytree(media_root, output / 'media')
        # Tell GitHub Pages to serve the files as they are.
        (output / '.nojekyll').touch()

        self.stdout.write(self.style.SUCCESS(f'Exported {pages} pages to {output}'))

    def _add_demo_data(self):
        """Create hero banners and featured products so the home page is complete."""
        banner_dir = Path(settings.MEDIA_ROOT) / 'banners'
        banner_dir.mkdir(parents=True, exist_ok=True)
        for order, name in enumerate(DEMO_HERO_BANNERS):
            source = Path(settings.BASE_DIR) / 'static' / 'images' / name
            shutil.copy(source, banner_dir / name)
            Banner.objects.get_or_create(
                image=f'banners/{name}',
                defaults={'position': Banner.POSITION_HERO, 'order': order},
            )
        featured = Product.objects.filter(stock__gt=0).order_by('id')[::20][:8]
        Product.objects.filter(pk__in=[p.pk for p in featured]).update(is_featured=True)

    def _crawl(self, base, output):
        """Save every page reachable from the home page; return the page count."""
        # Put every product of a list on a single page: "?page=N" links cannot
        # be served by a static host. Restored afterwards.
        original = CategoryView.paginate_by, ProductListView.paginate_by
        CategoryView.paginate_by = ProductListView.paginate_by = 10_000
        try:
            return self._crawl_from_home(base, output)
        finally:
            CategoryView.paginate_by, ProductListView.paginate_by = original

    def _crawl_from_home(self, base, output):
        client = Client()
        queue = [reverse('shop:home')]
        seen = set(queue)
        saved = 0
        while queue:
            url = queue.pop()
            # Links carry the prefix; the request path must not (it is added
            # back through FORCE_SCRIPT_NAME).
            response = client.get('/' + url[len(base):])
            if response.status_code != 200 or 'text/html' not in response['Content-Type']:
                continue
            html = response.content.decode()
            self._save(output, base, url, html)
            saved += 1
            for link in HREF_RE.findall(html):
                link = urldefrag(link.replace('&amp;', '&'))[0]
                if (link.startswith(base) and '?' not in link and link not in seen
                        and not link[len(base):].startswith(SKIPPED_PREFIXES)
                        and not link.startswith(settings.STATIC_URL)
                        and not link.startswith(settings.MEDIA_URL)):
                    seen.add(link)
                    queue.append(link)
        return saved

    def _write_404(self, output):
        html = Client().get('/__missing__/').content.decode()
        (output / '404.html').write_text(self._with_notice(html), encoding='utf-8')

    def _save(self, output, base, url, html):
        relative = unquote(url[len(base):]).strip('/')
        target = output / relative / 'index.html' if relative else output / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self._with_notice(html), encoding='utf-8')

    @staticmethod
    def _with_notice(html):
        return html.replace('<body>', '<body>' + DEMO_NOTICE, 1)

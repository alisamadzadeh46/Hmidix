import shutil
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from .factories import make_product


class BuildStaticDemoTests(TestCase):
    def setUp(self):
        self.output = Path(tempfile.mkdtemp()) / 'site'
        self.addCleanup(shutil.rmtree, self.output.parent)

    def test_exports_pages_under_base_path(self):
        product = make_product(slug='demo-cam')
        call_command('build_static_demo', output=str(self.output),
                     base_path='/Hmidix/', verbosity=0)

        home = (self.output / 'index.html').read_text(encoding='utf-8')
        self.assertIn('href="/Hmidix/static/css/main.css', home)
        self.assertIn('نسخه‌ی نمایشی', home)
        self.assertTrue((self.output / 'product' / 'demo-cam' / 'index.html').exists())
        self.assertTrue((self.output / '404.html').exists())
        self.assertTrue((self.output / 'static' / 'css' / 'main.css').exists())
        self.assertIn(product.name, home)

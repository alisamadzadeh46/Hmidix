from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Banner(models.Model):
    """A banner image managed from the admin.

    Two positions are supported:
      * hero  → large rotating slider at the top of the home page
      * promo → smaller promotional banners shown in a row below the slider
    """

    POSITION_HERO = 'hero'
    POSITION_PROMO = 'promo'
    POSITION_CHOICES = [
        (POSITION_HERO, 'اسلایدر بزرگ (بالای صفحه)'),
        (POSITION_PROMO, 'بنر کوچک (تبلیغاتی)'),
    ]

    title = models.CharField('عنوان', max_length=150, blank=True)
    position = models.CharField('جایگاه', max_length=10, choices=POSITION_CHOICES,
                                default=POSITION_HERO)
    image = models.ImageField('تصویر', upload_to='banners/')
    link = models.CharField('لینک مقصد', max_length=300, blank=True,
                            help_text='اختیاری؛ مثلاً /products/ یا آدرس کامل')
    order = models.PositiveIntegerField('ترتیب نمایش', default=0)
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = 'بنر'
        verbose_name_plural = 'بنرها'
        ordering = ['position', 'order', '-id']

    def __str__(self):
        return self.title or f'{self.get_position_display()} #{self.pk}'


class Category(models.Model):
    """A top-level product category shown in the main navigation."""

    name = models.CharField('نام دسته', max_length=120)
    slug = models.SlugField('اسلاگ', max_length=140, unique=True, allow_unicode=True)
    icon = models.CharField('کلاس آیکن', max_length=60, blank=True,
                            help_text='مثلاً fa-star')
    banner = models.ImageField('بنر', upload_to='banners/', blank=True, null=True)
    order = models.PositiveIntegerField('ترتیب نمایش', default=0)
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = 'دسته‌بندی'
        verbose_name_plural = 'دسته‌بندی‌ها'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('shop:category', kwargs={'slug': self.slug})


class Attribute(models.Model):
    """A dynamic, admin-managed product characteristic.

    Drives both the filter sidebar (e.g. مگاپیکسل، دید در شب، میکروفون) and the
    technical-spec table on the product page. Attach it to one or more categories
    so its filter only shows where relevant (empty = shown for all categories).
    """

    name = models.CharField('نام ویژگی', max_length=100)
    slug = models.SlugField('اسلاگ', max_length=120, unique=True, allow_unicode=True)
    unit = models.CharField('واحد', max_length=30, blank=True,
                            help_text='اختیاری؛ مثلاً مگاپیکسل یا متر')
    categories = models.ManyToManyField(
        Category, blank=True, related_name='attributes', verbose_name='دسته‌بندی‌ها',
        help_text='خالی بگذارید تا برای همهٔ دسته‌ها نمایش داده شود',
    )
    is_filterable = models.BooleanField('نمایش در فیلترها', default=True)
    show_in_specs = models.BooleanField('نمایش در مشخصات فنی', default=True)
    order = models.PositiveIntegerField('ترتیب نمایش', default=0)

    class Meta:
        verbose_name = 'ویژگی'
        verbose_name_plural = 'ویژگی‌ها'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class AttributeValue(models.Model):
    """A selectable value for an attribute (e.g. "4" for megapixels, "yes" for night vision)."""

    attribute = models.ForeignKey(
        Attribute, on_delete=models.CASCADE, related_name='values', verbose_name='ویژگی',
    )
    value = models.CharField('مقدار', max_length=100)
    order = models.PositiveIntegerField('ترتیب', default=0)

    class Meta:
        verbose_name = 'مقدار ویژگی'
        verbose_name_plural = 'مقادیر ویژگی'
        ordering = ['attribute', 'order', 'value']
        unique_together = [('attribute', 'value')]

    def __str__(self):
        return f'{self.attribute.name}: {self.value}'


class Product(models.Model):
    """A single product for sale."""

    STATUS_ACTIVE = 'active'
    STATUS_LOW = 'low'
    STATUS_OUT = 'out'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'موجود'),
        (STATUS_LOW, 'موجودی کم'),
        (STATUS_OUT, 'ناموجود'),
    ]

    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='products',
        verbose_name='دسته‌بندی',
    )
    name = models.CharField('نام محصول', max_length=255)
    slug = models.SlugField('اسلاگ', max_length=280, unique=True, allow_unicode=True)
    model_code = models.CharField('کد مدل', max_length=80, blank=True)
    image = models.ImageField('تصویر', upload_to='products/', blank=True, null=True)
    description = models.TextField('توضیحات', blank=True)
    price = models.BigIntegerField('قیمت (ریال)', default=0)
    old_price = models.BigIntegerField('قیمت قبلی (ریال)', null=True, blank=True)
    colleague_price = models.BigIntegerField(
        'قیمت همکار (ریال)', null=True, blank=True,
        help_text='قیمت ویژهٔ کاربران همکار؛ خالی بگذارید تا همان قیمت عادی اعمال شود',
    )
    call_for_price = models.BooleanField(
        'استعلام قیمت (تماس بگیرید)', default=False,
        help_text='برای محصولات با قیمت دلاری/متغیر؛ به‌جای قیمت، پیام «تماس بگیرید» نمایش داده می‌شود',
    )
    stock = models.PositiveIntegerField('موجودی', default=0)
    status = models.CharField('وضعیت', max_length=10, choices=STATUS_CHOICES,
                              default=STATUS_ACTIVE)
    is_featured = models.BooleanField('نمایش در صفحه اصلی', default=False)
    badge = models.CharField('برچسب', max_length=40, blank=True,
                             help_text='مثلاً پرفروش')
    attribute_values = models.ManyToManyField(
        AttributeValue, blank=True, related_name='products', verbose_name='ویژگی‌ها',
    )
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)

    class Meta:
        verbose_name = 'محصول'
        verbose_name_plural = 'محصولات'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.model_code or self.name, allow_unicode=True)
            self.slug = base or slugify(self.name, allow_unicode=True)
        if self.stock == 0:
            self.status = self.STATUS_OUT
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('shop:product_detail', kwargs={'slug': self.slug})

    @property
    def discount_percent(self):
        if self.old_price and self.old_price > self.price:
            return round((self.old_price - self.price) / self.old_price * 100)
        return 0

    @property
    def in_stock(self):
        return self.stock > 0 and self.status != self.STATUS_OUT

    def price_for(self, user):
        """Return the price this user should see/pay.

        Colleague users get the colleague price when it is set; everyone else
        gets the normal price. ``call_for_price`` only adds a warning note (the
        price is still shown), so it does not affect the value returned here.
        """
        if (getattr(user, 'is_authenticated', False)
                and getattr(user, 'is_colleague', False) and self.colleague_price):
            return self.colleague_price
        return self.price

    @property
    def approved_reviews(self):
        return self.reviews.filter(is_approved=True)

    @property
    def specs(self):
        """Group the product's attribute values by attribute for the spec table.

        Returns a list of (attribute, [values]) sorted by the attribute order.
        Prefetch ``attribute_values__attribute`` in the view to avoid N+1 queries.
        """
        groups = {}
        for av in self.attribute_values.all():
            attr = av.attribute
            if not attr.show_in_specs:
                continue
            groups.setdefault(attr.id, (attr, []))[1].append(av)
        ordered = sorted(groups.values(), key=lambda g: (g[0].order, g[0].name))
        return ordered


class ProductImage(models.Model):
    """An additional image shown in the product gallery."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name='images', verbose_name='محصول')
    image = models.ImageField('تصویر', upload_to='products/')
    order = models.PositiveSmallIntegerField('ترتیب', default=0)

    class Meta:
        verbose_name = 'تصویر محصول'
        verbose_name_plural = 'تصاویر محصول'
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.product.name} — تصویر {self.pk}'


class Review(models.Model):
    """A product review/comment left by a user."""

    RATING_CHOICES = [(i, f'{i} ستاره') for i in range(1, 6)]

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='reviews',
        verbose_name='محصول',
    )
    user = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='reviews',
        verbose_name='کاربر',
    )
    rating = models.PositiveSmallIntegerField('امتیاز', choices=RATING_CHOICES, default=5)
    text = models.TextField('نظر')
    is_approved = models.BooleanField('تأیید شده', default=False)
    created_at = models.DateTimeField('تاریخ', auto_now_add=True)

    class Meta:
        verbose_name = 'نظر'
        verbose_name_plural = 'نظرات'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.get_short_name()} - {self.product.name}'

from django.conf import settings
from django.db import models
from django.utils import timezone

from shop.models import Product


class Coupon(models.Model):
    """A discount code applied to a cart at checkout."""

    TYPE_PERCENT = 'percent'
    TYPE_FIXED = 'fixed'
    TYPE_CHOICES = [
        (TYPE_PERCENT, 'درصدی'),
        (TYPE_FIXED, 'مبلغ ثابت (ریال)'),
    ]

    code = models.CharField('کد تخفیف', max_length=40, unique=True)
    discount_type = models.CharField('نوع تخفیف', max_length=10,
                                     choices=TYPE_CHOICES, default=TYPE_PERCENT)
    value = models.BigIntegerField('مقدار', help_text='درصد (۰ تا ۱۰۰) یا مبلغ ریالی')
    min_amount = models.BigIntegerField('حداقل مبلغ سبد (ریال)', default=0)
    active = models.BooleanField('فعال', default=True)
    valid_from = models.DateTimeField('معتبر از', null=True, blank=True)
    valid_to = models.DateTimeField('معتبر تا', null=True, blank=True)
    max_uses = models.PositiveIntegerField('حداکثر دفعات استفاده', null=True, blank=True,
                                           help_text='خالی = نامحدود')
    used_count = models.PositiveIntegerField('دفعات استفاده‌شده', default=0)

    class Meta:
        verbose_name = 'کد تخفیف'
        verbose_name_plural = 'کدهای تخفیف'

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def validate_for(self, amount):
        """Return (is_valid, error_message) for the given cart amount."""
        now = timezone.now()
        if not self.active:
            return False, 'این کد تخفیف غیرفعال است.'
        if self.valid_from and now < self.valid_from:
            return False, 'این کد تخفیف هنوز فعال نشده است.'
        if self.valid_to and now > self.valid_to:
            return False, 'این کد تخفیف منقضی شده است.'
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False, 'ظرفیت استفاده از این کد تخفیف پر شده است.'
        if amount < self.min_amount:
            return False, f'حداقل مبلغ سبد برای این کد {self.min_amount:,} ریال است.'
        return True, ''

    def discount_amount(self, amount):
        if self.discount_type == self.TYPE_PERCENT:
            disc = amount * self.value // 100
        else:
            disc = self.value
        return min(disc, amount)


class Order(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_SHIPPED = 'shipped'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'در انتظار پرداخت'),
        (STATUS_PAID, 'پرداخت شده'),
        (STATUS_SHIPPED, 'ارسال شده'),
        (STATUS_CANCELLED, 'لغو شده'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='orders', verbose_name='کاربر',
    )
    full_name = models.CharField('نام گیرنده', max_length=150)
    phone = models.CharField('شماره تماس', max_length=11)
    address = models.TextField('آدرس')
    status = models.CharField('وضعیت', max_length=10, choices=STATUS_CHOICES,
                              default=STATUS_PENDING)
    coupon = models.ForeignKey('orders.Coupon', on_delete=models.SET_NULL, null=True,
                               blank=True, related_name='orders', verbose_name='کد تخفیف')
    discount = models.BigIntegerField('مبلغ تخفیف (ریال)', default=0)
    total = models.BigIntegerField('مبلغ قابل پرداخت (ریال)', default=0)
    authority = models.CharField('کد authority زرین‌پال', max_length=50, blank=True)
    ref_id = models.BigIntegerField('شماره پیگیری', null=True, blank=True)
    tracking_code = models.CharField(
        'کد رهگیری پستی', max_length=50, blank=True,
        help_text='کد رهگیری پست یا تیپاکس؛ پس از ارسال سفارش وارد کنید',
    )
    created_at = models.DateTimeField('تاریخ ثبت', auto_now_add=True)

    class Meta:
        verbose_name = 'سفارش'
        verbose_name_plural = 'سفارش‌ها'
        ordering = ['-created_at']

    def __str__(self):
        return f'کد سفارش {self.pk} — {self.full_name}'

    @property
    def items_total(self):
        return sum(item.line_total for item in self.items.all())

    def recalculate_total(self):
        self.total = self.items_total - self.discount
        return self.total


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, related_name='order_items',
    )
    name = models.CharField('نام محصول', max_length=255)
    price = models.BigIntegerField('قیمت واحد (ریال)', default=0)
    quantity = models.PositiveIntegerField('تعداد', default=1)

    class Meta:
        verbose_name = 'قلم سفارش'
        verbose_name_plural = 'اقلام سفارش'

    def __str__(self):
        return f'{self.name} × {self.quantity}'

    @property
    def line_total(self):
        return (self.price or 0) * self.quantity

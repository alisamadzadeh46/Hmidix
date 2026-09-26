from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(
    regex=r'^09\d{9}$',
    message='شماره تلفن باید با ۰۹ شروع شده و ۱۱ رقم باشد.',
)


class UserManager(BaseUserManager):
    """User manager that uses the phone number as the unique identifier."""

    use_in_migrations = True

    def _create_user(self, phone, password, **extra_fields):
        if not phone:
            raise ValueError('شماره تلفن الزامی است.')
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(phone, password, **extra_fields)


class User(AbstractUser):
    """Custom user authenticated by phone number instead of username."""

    ROLE_NORMAL = 'normal'
    ROLE_COLLEAGUE = 'colleague'
    ROLE_CHOICES = [
        (ROLE_NORMAL, 'عادی'),
        (ROLE_COLLEAGUE, 'همکار'),
    ]

    username = None
    phone = models.CharField(
        'شماره تلفن', max_length=11, unique=True, validators=[phone_validator]
    )
    full_name = models.CharField('نام و نام خانوادگی', max_length=150, blank=True)
    role = models.CharField('نوع کاربر', max_length=10, choices=ROLE_CHOICES,
                            default=ROLE_NORMAL,
                            help_text='کاربران همکار قیمت ویژهٔ همکاری را می‌بینند')

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'

    def __str__(self):
        return self.full_name or self.phone

    def get_short_name(self):
        return self.full_name or self.phone

    @property
    def is_colleague(self):
        return self.role == self.ROLE_COLLEAGUE


class Address(models.Model):
    """A saved shipping address belonging to a user."""

    user = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='addresses',
        verbose_name='کاربر',
    )
    title = models.CharField('عنوان آدرس', max_length=60,
                             help_text='مثلاً خانه، محل کار')
    receiver = models.CharField('نام گیرنده', max_length=150)
    phone = models.CharField('شماره تماس', max_length=11, validators=[phone_validator])
    province = models.CharField('استان', max_length=60)
    city = models.CharField('شهر', max_length=60)
    postal_code = models.CharField('کد پستی', max_length=10, blank=True)
    address = models.TextField('نشانی کامل')
    is_default = models.BooleanField('آدرس پیش‌فرض', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'آدرس'
        verbose_name_plural = 'آدرس‌ها'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f'{self.title} - {self.city}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Ensure only one default address per user.
        if self.is_default:
            Address.objects.filter(user=self.user).exclude(pk=self.pk).update(
                is_default=False
            )

    @property
    def full_line(self):
        parts = [self.province, self.city, self.address]
        return '، '.join(p for p in parts if p)

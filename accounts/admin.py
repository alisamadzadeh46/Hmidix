from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Address, User


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'receiver', 'city', 'is_default', 'created_at')
    list_filter = ('is_default', 'province')
    search_fields = ('receiver', 'city', 'user__phone')
    autocomplete_fields = ('user',)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ('phone',)
    list_display = ('phone', 'full_name', 'role', 'is_staff', 'is_active', 'date_joined')
    list_editable = ('role',)
    search_fields = ('phone', 'full_name')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('اطلاعات شخصی', {'fields': ('full_name', 'email')}),
        ('نوع کاربر', {'fields': ('role',)}),
        ('دسترسی‌ها', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('تاریخ‌ها', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'full_name', 'role', 'password1', 'password2'),
        }),
    )

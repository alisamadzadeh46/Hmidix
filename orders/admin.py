from django.contrib import admin

from .models import Coupon, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('line_total',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_code', 'full_name', 'phone', 'status', 'tracking_code',
                    'total', 'created_at')
    list_display_links = ('order_code', 'full_name')
    list_filter = ('status', 'created_at')
    search_fields = ('full_name', 'phone', 'id', 'tracking_code')
    readonly_fields = ('discount', 'total', 'created_at')
    inlines = [OrderItemInline]
    list_editable = ('status', 'tracking_code')

    @admin.display(description='کد سفارش', ordering='id')
    def order_code(self, obj):
        return obj.pk


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'value', 'min_amount', 'active',
                    'used_count', 'max_uses', 'valid_to')
    list_editable = ('active',)
    list_filter = ('active', 'discount_type')
    search_fields = ('code',)
    readonly_fields = ('used_count',)

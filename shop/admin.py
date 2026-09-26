from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Attribute, AttributeValue, Banner, Category, Product, ProductImage, Review,
)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('thumb', 'title', 'position', 'order', 'is_active')
    list_display_links = ('thumb', 'title')
    list_editable = ('order', 'is_active')
    list_filter = ('position', 'is_active')

    @admin.display(description='پیش‌نمایش')
    def thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:46px;border-radius:6px;" />', obj.image.url
            )
        return '—'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order', 'is_active', 'product_count')
    list_editable = ('order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

    @admin.display(description='تعداد محصول')
    def product_count(self, obj):
        return obj.products.count()


class AttributeValueInline(admin.TabularInline):
    model = AttributeValue
    extra = 3
    fields = ('value', 'order')


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    inlines = [AttributeValueInline]
    list_display = ('name', 'unit', 'value_count', 'is_filterable', 'show_in_specs', 'order')
    list_editable = ('is_filterable', 'show_in_specs', 'order')
    list_filter = ('is_filterable', 'show_in_specs', 'categories')
    filter_horizontal = ('categories',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

    @admin.display(description='تعداد مقادیر')
    def value_count(self, obj):
        return obj.values.count()


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ('image', 'order')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]
    list_display = ('thumb', 'name', 'category', 'price', 'colleague_price',
                    'call_for_price', 'stock', 'status', 'is_featured')
    list_display_links = ('thumb', 'name')
    list_editable = ('price', 'colleague_price', 'call_for_price', 'stock', 'status', 'is_featured')
    list_filter = ('category', 'status', 'is_featured', 'call_for_price')
    search_fields = ('name', 'model_code')
    prepopulated_fields = {'slug': ('model_code',)}
    autocomplete_fields = ('category',)
    filter_horizontal = ('attribute_values',)
    readonly_fields = ('created_at',)
    list_per_page = 10

    @admin.display(description='تصویر')
    def thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:40px;border-radius:6px;" />',
                obj.image.url,
            )
        return '—'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'rating', 'created_at')
    list_editable = ('is_approved',)
    search_fields = ('product__name', 'user__phone', 'text')
    autocomplete_fields = ('product', 'user')
    readonly_fields = ('created_at',)

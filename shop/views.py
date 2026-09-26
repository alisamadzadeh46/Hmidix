from collections import defaultdict

from django.contrib import messages
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from .forms import ReviewForm
from .models import Attribute, AttributeValue, Banner, Category, Product, Review


SORT_OPTIONS = [
    ('newest', 'جدیدترین'),
    ('bestselling', 'پرفروش‌ترین'),
    ('popular', 'محبوب‌ترین'),
    ('cheapest', 'ارزان‌ترین'),
    ('expensive', 'گران‌ترین'),
]
SORT_FIELDS = {
    'newest': '-created_at',
    'bestselling': '-sold',
    'popular': '-review_count',
    'cheapest': 'price',
    'expensive': '-price',
}


class ProductFilterMixin:
    """Shared dynamic filtering + sorting for the category and search list views.

    Filters come from the query string:
      * ``attr`` (repeatable) — AttributeValue ids (AND across attributes, OR within one)
      * ``min_price`` / ``max_price`` — price range in rials
      * ``in_stock`` — only available products
      * ``sort`` — one of SORT_FIELDS
    """

    category = None

    def filter_and_sort(self, qs):
        from orders.models import OrderItem  # local import avoids app-load cycle

        req = self.request.GET

        # price range
        for param, lookup in (('min_price', 'price__gte'), ('max_price', 'price__lte')):
            raw = req.get(param, '').strip()
            if raw.isdigit():
                qs = qs.filter(**{lookup: int(raw)})

        # availability
        if req.get('in_stock'):
            qs = qs.filter(stock__gt=0).exclude(status=Product.STATUS_OUT)

        # dynamic attribute filters — AND between attributes, OR inside one attribute
        value_ids = [v for v in req.getlist('attr') if v.isdigit()]
        if value_ids:
            pairs = AttributeValue.objects.filter(id__in=value_ids).values_list(
                'attribute_id', 'id')
            groups = defaultdict(list)
            for attr_id, val_id in pairs:
                groups[attr_id].append(val_id)
            for vids in groups.values():
                qs = qs.filter(attribute_values__in=vids)
            qs = qs.distinct()

        # subquery annotations (subqueries don't inflate with the attribute joins)
        sold_sq = (
            OrderItem.objects
            .filter(product_id=OuterRef('pk'), order__status__in=['paid', 'shipped'])
            .values('product_id').annotate(t=Sum('quantity')).values('t')
        )
        review_sq = (
            Review.objects
            .filter(product_id=OuterRef('pk'), is_approved=True)
            .values('product_id').annotate(c=Count('id')).values('c')
        )
        qs = qs.annotate(
            sold=Coalesce(Subquery(sold_sq, output_field=IntegerField()), 0),
            review_count=Coalesce(Subquery(review_sq, output_field=IntegerField()), 0),
        )

        sort = req.get('sort', 'newest')
        return qs.order_by(SORT_FIELDS.get(sort, '-created_at'), '-id')

    def filter_context(self):
        req = self.request.GET
        attrs = Attribute.objects.filter(is_filterable=True)
        if self.category is not None:
            attrs = attrs.filter(Q(categories=self.category) | Q(categories__isnull=True))
        attrs = attrs.distinct().prefetch_related('values')

        selected = set(req.getlist('attr'))
        filter_groups = []
        for attr in attrs:
            values = [
                {'id': v.id, 'value': v.value, 'checked': str(v.id) in selected}
                for v in attr.values.all()
            ]
            if values:
                filter_groups.append({'attribute': attr, 'values': values})

        return {
            'filter_groups': filter_groups,
            'sort_options': SORT_OPTIONS,
            'selected_sort': req.get('sort', 'newest'),
            'min_price': req.get('min_price', ''),
            'max_price': req.get('max_price', ''),
            'in_stock_checked': bool(req.get('in_stock')),
            'has_active_filters': bool(
                req.getlist('attr') or req.get('min_price')
                or req.get('max_price') or req.get('in_stock')
            ),
        }


class HomeView(TemplateView):
    template_name = 'shop/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        categories = Category.objects.filter(is_active=True).prefetch_related('products')
        sections = []
        for category in categories:
            products = list(category.products.all()[:8])
            if products:
                sections.append({'category': category, 'products': products})
        ctx['sections'] = sections
        ctx['featured'] = Product.objects.filter(is_featured=True)[:8]
        active_banners = Banner.objects.filter(is_active=True)
        ctx['hero_banners'] = active_banners.filter(position=Banner.POSITION_HERO)
        ctx['promo_banners'] = active_banners.filter(position=Banner.POSITION_PROMO)
        return ctx


class CategoryView(ProductFilterMixin, ListView):
    template_name = 'shop/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['slug'], is_active=True)
        qs = Product.objects.filter(category=self.category).select_related('category')
        return self.filter_and_sort(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['category'] = self.category
        ctx['page_title'] = self.category.name
        ctx.update(self.filter_context())
        return ctx


class ProductListView(ProductFilterMixin, ListView):
    """All products, optionally filtered by ?q= search term."""

    template_name = 'shop/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        qs = Product.objects.select_related('category').all()
        self.query = self.request.GET.get('q', '').strip()
        if self.query:
            qs = qs.filter(
                Q(name__icontains=self.query)
                | Q(model_code__icontains=self.query)
                | Q(description__icontains=self.query)
            )
        return self.filter_and_sort(qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['query'] = self.query
        ctx['page_title'] = (
            f'نتایج جستجو برای «{self.query}»' if self.query else 'همه محصولات'
        )
        ctx.update(self.filter_context())
        return ctx


class ProductDetailView(DetailView):
    model = Product
    template_name = 'shop/product_detail.html'
    context_object_name = 'product'

    def get_queryset(self):
        return Product.objects.select_related('category').prefetch_related(
            'attribute_values__attribute')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['related'] = (
            Product.objects.filter(category=self.object.category)
            .exclude(pk=self.object.pk)[:4]
        )
        ctx['reviews'] = self.object.reviews.filter(is_approved=True).select_related('user')
        ctx.setdefault('review_form', ReviewForm())
        return ctx


class ReviewCreateView(View):
    """Handle a review submission from the product detail page."""

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        if not request.user.is_authenticated:
            messages.warning(request, 'برای ثبت نظر ابتدا وارد شوید.')
            return redirect(f"{request.build_absolute_uri('/auth/login/')}"
                            f"?next={product.get_absolute_url()}")
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, 'نظر شما ثبت شد و پس از تأیید نمایش داده می‌شود.')
        else:
            messages.error(request, 'لطفاً متن نظر را وارد کنید.')
        return redirect(product.get_absolute_url())


class AboutView(TemplateView):
    template_name = 'shop/about.html'


class ContactView(TemplateView):
    template_name = 'shop/contact.html'


class HowToOrderView(TemplateView):
    template_name = 'shop/how_to_order.html'


class ShippingPolicyView(TemplateView):
    template_name = 'shop/shipping_policy.html'


class PaymentMethodsView(TemplateView):
    template_name = 'shop/payment_methods.html'

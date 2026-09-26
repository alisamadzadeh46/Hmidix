from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, TemplateView

from accounts.models import Address
from core.http import parse_int, referer_or
from shop.models import Product

from .cart import Cart
from .forms import CheckoutForm
from .models import Coupon, Order, OrderItem
from .payments import get_gateway


def is_ajax(request):
    """Return True for requests sent by the storefront's fetch() calls."""
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def cart_summary(cart):
    """JSON payload describing the cart after an AJAX change."""
    return {'count': len(cart), 'total': cart.total}


class CartView(TemplateView):
    template_name = 'orders/cart.html'


class CartAddView(View):
    """Add a product to the cart. Returns JSON for AJAX, redirects otherwise."""

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        if product.call_for_price:
            msg = 'برای ثبت سفارش این محصول لطفاً با ما تماس بگیرید.'
            if is_ajax(request):
                return JsonResponse({'error': msg}, status=400)
            messages.warning(request, msg)
            return redirect(product.get_absolute_url())

        quantity = parse_int(request.POST.get('quantity'), default=1, minimum=1)
        replace = request.POST.get('replace') == 'true'
        cart = Cart(request)
        cart.add(product, quantity=quantity, replace=replace)

        if is_ajax(request):
            return JsonResponse(cart_summary(cart))
        messages.success(request, f'«{product.name}» به سبد خرید اضافه شد.')
        return redirect(referer_or(request, 'shop:home'))


class CartUpdateView(View):
    """Set an absolute quantity for a cart line (used by + / − controls)."""

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        quantity = parse_int(request.POST.get('quantity'), default=0)
        Cart(request).set_quantity(product, quantity)
        return redirect('orders:cart')


class CartRemoveView(View):
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        cart = Cart(request)
        cart.remove(product)
        if is_ajax(request):
            return JsonResponse(cart_summary(cart))
        return redirect('orders:cart')


class CouponApplyView(View):
    def post(self, request):
        code = request.POST.get('code', '').strip().upper()
        cart = Cart(request)
        coupon = Coupon.objects.filter(code=code).first()
        if not coupon:
            messages.error(request, 'کد تخفیف نامعتبر است.')
        else:
            ok, error = coupon.validate_for(cart.subtotal)
            if ok:
                cart.apply_coupon(coupon)
                messages.success(request, 'کد تخفیف اعمال شد.')
            else:
                messages.error(request, error)
        return redirect(referer_or(request, 'orders:cart'))


class CouponRemoveView(View):
    def post(self, request):
        Cart(request).remove_coupon()
        messages.info(request, 'کد تخفیف حذف شد.')
        return redirect(referer_or(request, 'orders:cart'))


class CheckoutView(LoginRequiredMixin, TemplateView):
    """Collect the delivery address and turn the cart into an order."""

    template_name = 'orders/checkout.html'

    def dispatch(self, request, *args, **kwargs):
        # Authenticate before inspecting the cart; the mixin's own check only
        # runs later, inside super().dispatch().
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.cart = Cart(request)
        if len(self.cart) == 0:
            messages.warning(request, 'سبد خرید شما خالی است.')
            return redirect('shop:product_list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['addresses'] = self.request.user.addresses.all()
        ctx['form'] = kwargs.get('form') or CheckoutForm(initial=self._initial())
        return ctx

    def _initial(self):
        user = self.request.user
        default = user.addresses.filter(is_default=True).first() or user.addresses.first()
        if default:
            return {'full_name': default.receiver, 'phone': default.phone,
                    'address': default.full_line}
        return {'full_name': user.full_name, 'phone': user.phone}

    def post(self, request, *args, **kwargs):
        user = request.user

        # A saved address was chosen: build the order from it directly.
        address_id = request.POST.get('address_id')
        if address_id:
            address = get_object_or_404(Address, pk=address_id, user=user)
            return self._create_order(address.receiver, address.phone, address.full_line)

        form = CheckoutForm(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        data = form.cleaned_data
        if request.POST.get('save_address'):
            Address.objects.create(
                user=user, title=data.get('full_name') or 'آدرس جدید',
                receiver=data['full_name'], phone=data['phone'],
                province='', city='', address=data['address'],
            )
        return self._create_order(data['full_name'], data['phone'], data['address'])

    def _create_order(self, full_name, phone, address):
        cart = self.cart
        coupon = cart.coupon
        with transaction.atomic():
            order = Order.objects.create(
                user=self.request.user,
                full_name=full_name, phone=phone, address=address,
                coupon=coupon, discount=cart.discount,
            )
            OrderItem.objects.bulk_create([
                OrderItem(
                    order=order, product=item['product'], name=item['product'].name,
                    price=item['unit_price'], quantity=item['quantity'],
                )
                for item in cart
            ])
            order.recalculate_total()
            order.save(update_fields=['total'])
            if coupon:
                # Increment in the database to avoid lost updates under concurrency.
                Coupon.objects.filter(pk=coupon.pk).update(used_count=F('used_count') + 1)
        cart.clear()
        return redirect('orders:payment_start', pk=order.pk)


class OrderOwnerMixin(LoginRequiredMixin):
    """Restrict order views to the order's owner (staff can see every order)."""

    def get_order_queryset(self):
        qs = Order.objects.all()
        user = self.request.user
        return qs if user.is_staff else qs.filter(user=user)


class PaymentStartView(OrderOwnerMixin, View):
    """Request a payment authority from the gateway and redirect the user to it."""

    def get(self, request, pk):
        order = get_object_or_404(self.get_order_queryset(), pk=pk)

        # Guard against paying the same order twice.
        if order.status == Order.STATUS_PAID:
            messages.info(request, 'این سفارش قبلاً پرداخت شده است.')
            return redirect(order)

        gateway = get_gateway()
        callback_url = request.build_absolute_uri(
            reverse('orders:payment_verify', kwargs={'pk': order.pk})
        )
        authority, error = gateway.payment_request(
            amount=order.total,
            description=f'پرداخت سفارش کد {order.pk} - {order.full_name}',
            callback_url=callback_url,
            mobile=order.phone or None,
            email=(order.user.email if order.user else None) or None,
        )
        if error:
            messages.error(request, f'خطا در اتصال به درگاه پرداخت: {error}')
            return redirect(order)

        order.authority = authority
        order.save(update_fields=['authority'])
        return redirect(gateway.gateway_url(authority))


class PaymentVerifyView(View):
    """Verify the payment when the user returns from the gateway.

    Not login-protected on purpose: the customer's session may have expired
    while paying. The order is only marked paid after the gateway confirms the
    authority that was issued for this very order.
    """

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        status = request.GET.get('Status')
        authority = request.GET.get('Authority', '')

        if status != 'OK' or not order.authority or authority != order.authority:
            messages.error(request, 'پرداخت لغو شد یا ناموفق بود.')
            return redirect(order)

        if order.status == Order.STATUS_PAID:
            messages.info(request, 'این سفارش قبلاً تأیید شده است.')
            return redirect(order)

        ref_id, error = get_gateway().payment_verify(
            amount=order.total, authority=order.authority,
        )
        if error:
            messages.error(request, f'تأیید پرداخت ناموفق بود: {error}')
            return redirect(order)

        order.status = Order.STATUS_PAID
        order.ref_id = ref_id
        order.save(update_fields=['status', 'ref_id'])
        messages.success(request, f'پرداخت موفق! شماره پیگیری: {ref_id}')
        return redirect(order)


class OrderDetailView(OrderOwnerMixin, DetailView):
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return self.get_order_queryset().prefetch_related('items')

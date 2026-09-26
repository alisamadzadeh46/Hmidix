from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, TemplateView

from accounts.models import Address
from shop.models import Product

from .cart import Cart
from .forms import CheckoutForm
from .models import Coupon, Order, OrderItem
from . import zarinpal


class CartView(TemplateView):
    template_name = 'orders/cart.html'


class CartAddView(View):
    """Add a product to the cart. Returns JSON for AJAX, redirects otherwise."""

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        if product.call_for_price:
            msg = 'برای ثبت سفارش این محصول لطفاً با ما تماس بگیرید.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': msg}, status=400)
            messages.warning(request, msg)
            return redirect(product.get_absolute_url())
        quantity = int(request.POST.get('quantity', 1) or 1)
        replace = request.POST.get('replace') == 'true'
        cart = Cart(request)
        cart.add(product, quantity=quantity, replace=replace)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'count': len(cart), 'total': cart.total})
        messages.success(request, f'«{product.name}» به سبد خرید اضافه شد.')
        return redirect(request.META.get('HTTP_REFERER', 'shop:home'))


class CartUpdateView(View):
    """Set an absolute quantity for a cart line (used by + / − controls)."""

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        quantity = int(request.POST.get('quantity', 1) or 0)
        cart = Cart(request)
        cart.set_quantity(product, quantity)
        return redirect('orders:cart')


class CartRemoveView(View):
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        cart = Cart(request)
        cart.remove(product)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'count': len(cart), 'total': cart.total})
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
        return redirect(request.META.get('HTTP_REFERER', 'orders:cart'))


class CouponRemoveView(View):
    def post(self, request):
        Cart(request).remove_coupon()
        messages.info(request, 'کد تخفیف حذف شد.')
        return redirect(request.META.get('HTTP_REFERER', 'orders:cart'))


class CheckoutView(TemplateView):
    template_name = 'orders/checkout.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.urls import reverse as _reverse
            return redirect(f"{_reverse('accounts:login')}?next={_reverse('orders:checkout')}")
        self.cart = Cart(request)
        if len(self.cart) == 0:
            messages.warning(request, 'سبد خرید شما خالی است.')
            return redirect('shop:product_list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['addresses'] = (user.addresses.all() if user.is_authenticated else [])
        ctx['form'] = kwargs.get('form') or CheckoutForm(initial=self._initial())
        return ctx

    def _initial(self):
        user = self.request.user
        if user.is_authenticated:
            default = user.addresses.filter(is_default=True).first() or user.addresses.first()
            if default:
                return {'full_name': default.receiver, 'phone': default.phone,
                        'address': default.full_line}
            return {'full_name': user.full_name, 'phone': user.phone}
        return {}

    def post(self, request, *args, **kwargs):
        user = request.user
        address_id = request.POST.get('address_id')

        # If a saved address was chosen, build the order from it directly.
        if address_id and user.is_authenticated:
            address = get_object_or_404(Address, pk=address_id, user=user)
            return self._create_order(request, address.receiver, address.phone,
                                      address.full_line)

        form = CheckoutForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            # Optionally save the new address to the user's profile.
            if user.is_authenticated and request.POST.get('save_address'):
                Address.objects.create(
                    user=user, title=cd.get('full_name') or 'آدرس جدید',
                    receiver=cd['full_name'], phone=cd['phone'],
                    province='', city='', address=cd['address'],
                )
            return self._create_order(request, cd['full_name'], cd['phone'], cd['address'])
        return self.render_to_response(self.get_context_data(form=form))

    def _create_order(self, request, full_name, phone, address):
        cart = self.cart
        coupon = cart.coupon
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                full_name=full_name, phone=phone, address=address,
                coupon=coupon, discount=cart.discount,
            )
            for item in cart:
                product = item['product']
                OrderItem.objects.create(
                    order=order, product=product, name=product.name,
                    price=item['unit_price'], quantity=item['quantity'],
                )
            order.recalculate_total()
            order.save(update_fields=['total'])
            if coupon:
                Coupon.objects.filter(pk=coupon.pk).update(used_count=coupon.used_count + 1)
        cart.clear()
        return redirect('orders:payment_start', pk=order.pk)


class PaymentStartView(View):
    """Request a payment authority from the gateway and redirect the user to it."""

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)

        # Guard against paying the same order twice.
        if order.status == Order.STATUS_PAID:
            messages.info(request, 'این سفارش قبلاً پرداخت شده است.')
            return redirect('orders:order_detail', pk=order.pk)

        callback_url = request.build_absolute_uri(
            reverse('orders:payment_verify', kwargs={'pk': order.pk})
        )
        mobile = order.phone if order.phone else None
        email = order.user.email if order.user and order.user.email else None

        authority, error = zarinpal.payment_request(
            amount=order.total,
            description=f'پرداخت سفارش کد {order.pk} - {order.full_name}',
            callback_url=callback_url,
            mobile=mobile,
            email=email,
        )

        if error:
            messages.error(request, f'خطا در اتصال به درگاه پرداخت: {error}')
            return redirect('orders:order_detail', pk=order.pk)

        order.authority = authority
        order.save(update_fields=['authority'])
        return redirect(zarinpal.gateway_url(authority))


class PaymentVerifyView(View):
    """Verify the payment when the user returns from the gateway."""

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        status = request.GET.get('Status')
        authority = request.GET.get('Authority', '')

        if status != 'OK':
            messages.error(request, 'پرداخت لغو شد یا ناموفق بود.')
            return redirect('orders:order_detail', pk=order.pk)

        if order.status == Order.STATUS_PAID:
            messages.info(request, 'این سفارش قبلاً تأیید شده است.')
            return redirect('orders:order_detail', pk=order.pk)

        ref_id, error = zarinpal.payment_verify(
            amount=order.total,
            authority=authority or order.authority,
        )

        if error:
            messages.error(request, f'تأیید پرداخت ناموفق بود: {error}')
            return redirect('orders:order_detail', pk=order.pk)

        order.status = Order.STATUS_PAID
        order.ref_id = ref_id
        order.save(update_fields=['status', 'ref_id'])
        messages.success(request, f'پرداخت موفق! شماره پیگیری: {ref_id}')
        return redirect('orders:order_detail', pk=order.pk)


class OrderDetailView(DetailView):
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        qs = Order.objects.prefetch_related('items')
        if self.request.user.is_authenticated and not self.request.user.is_staff:
            return qs.filter(user=self.request.user)
        return qs

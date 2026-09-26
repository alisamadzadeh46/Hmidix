from shop.models import Product

from .models import Coupon

CART_SESSION_KEY = 'cart'
COUPON_SESSION_KEY = 'coupon_id'


class Cart:
    """A session-backed shopping cart.

    Stores {product_id: quantity} plus an optional applied coupon id in the
    session, and hydrates them with live data on access.
    """

    def __init__(self, request):
        self.session = request.session
        self.user = getattr(request, 'user', None)
        cart = self.session.get(CART_SESSION_KEY)
        if cart is None:
            cart = self.session[CART_SESSION_KEY] = {}
        self.cart = cart

    def unit_price(self, product):
        """Role-aware unit price (colleague price for colleague users)."""
        price = product.price_for(self.user)
        return price if price is not None else product.price

    def save(self):
        self.session[CART_SESSION_KEY] = self.cart
        self.session.modified = True

    def add(self, product, quantity=1, replace=False):
        pid = str(product.pk)
        current = self.cart.get(pid, 0)
        self.cart[pid] = quantity if replace else current + quantity
        if self.cart[pid] <= 0:
            self.cart.pop(pid, None)
        self.save()

    def set_quantity(self, product, quantity):
        pid = str(product.pk)
        if quantity <= 0:
            self.cart.pop(pid, None)
        else:
            self.cart[pid] = min(quantity, max(product.stock, 1))
        self.save()

    def remove(self, product):
        self.cart.pop(str(product.pk), None)
        self.save()

    def clear(self):
        self.session[CART_SESSION_KEY] = {}
        self.session.pop(COUPON_SESSION_KEY, None)
        self.session.modified = True

    def __iter__(self):
        products = Product.objects.filter(pk__in=self.cart.keys())
        for product in products:
            quantity = self.cart[str(product.pk)]
            unit_price = self.unit_price(product)
            yield {
                'product': product,
                'quantity': quantity,
                'unit_price': unit_price,
                'line_total': unit_price * quantity,
            }

    def __len__(self):
        return sum(self.cart.values())

    @property
    def subtotal(self):
        products = Product.objects.filter(pk__in=self.cart.keys())
        return sum(self.unit_price(p) * self.cart[str(p.pk)] for p in products)

    # ---- Coupon handling ----
    def apply_coupon(self, coupon):
        self.session[COUPON_SESSION_KEY] = coupon.pk
        self.session.modified = True

    def remove_coupon(self):
        self.session.pop(COUPON_SESSION_KEY, None)
        self.session.modified = True

    @property
    def coupon(self):
        cid = self.session.get(COUPON_SESSION_KEY)
        if not cid:
            return None
        coupon = Coupon.objects.filter(pk=cid).first()
        # Drop the coupon silently if it is no longer valid for the cart.
        if coupon:
            ok, _ = coupon.validate_for(self.subtotal)
            if ok:
                return coupon
            self.remove_coupon()
        return None

    @property
    def discount(self):
        coupon = self.coupon
        return coupon.discount_amount(self.subtotal) if coupon else 0

    @property
    def total(self):
        return self.subtotal - self.discount

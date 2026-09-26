from .cart import Cart


def cart(request):
    """Expose the current cart (count + total) to all templates."""
    current = Cart(request)
    return {
        'cart': current,
        'cart_count': len(current),
    }

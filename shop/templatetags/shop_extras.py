from django import template

register = template.Library()

_EN_FA = str.maketrans('0123456789,', '۰۱۲۳۴۵۶۷۸۹،')


@register.filter
def currency(value):
    """Format an integer price with comma thousands separators (e.g. 55,300,000)."""
    try:
        return f'{int(value):,}'
    except (TypeError, ValueError):
        return value


@register.filter
def fa_num(value):
    """Convert Western digits and commas to Persian equivalents."""
    return str(value).translate(_EN_FA)


@register.filter
def price_for(product, user):
    """Return the price a given user should see for a product (role-aware)."""
    return product.price_for(user)

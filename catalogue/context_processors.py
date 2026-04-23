# context_processors.py — Makes cart and membership data available in every template
# I register these in settings.py under TEMPLATES so Django calls them on every request

from .cart import Cart
from .decorators import has_pro_access, has_pro_plus_access


def cart(request):
    """Expose session cart in all templates for navbar counter."""
    # I return the cart here so I can access it in the navbar without passing it from every view
    return {'cart': Cart(request)}


def membership(request):
    """Expose membership capability flags and Pro feature copy to templates."""
    user = request.user
    return {
        'has_pro_access': has_pro_access(user),
        'has_pro_plus_access': has_pro_plus_access(user),
        # I use get attribute with a fallback so this doesn't crash if the user model doesn't have these attributes
        'pro_privileges': getattr(user, 'PRO_PRIVILEGES', ()),
        'pro_plus_privileges': getattr(user, 'PRO_PLUS_PRIVILEGES', ()),
    }
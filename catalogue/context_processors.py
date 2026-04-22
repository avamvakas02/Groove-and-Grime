from .cart import Cart
from .decorators import has_pro_access, has_pro_plus_access


def cart(request):
    """Expose session cart in all templates for navbar counter."""
    return {'cart': Cart(request)}


def membership(request):
    """Expose membership capability flags and Pro feature copy to templates."""
    user = request.user
    return {
        'has_pro_access': has_pro_access(user),
        'has_pro_plus_access': has_pro_plus_access(user),
        'pro_privileges': getattr(user, 'PRO_PRIVILEGES', ()),
        'pro_plus_privileges': getattr(user, 'PRO_PLUS_PRIVILEGES', ()),
    }

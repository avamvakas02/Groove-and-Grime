# decorators.py — Custom permission helpers and view decorators for access control
# I use these to protect views based on the user's membership tier

from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import redirect


def has_pro_access(user):
    """Shared rule for Pro-only member capabilities."""
    if not user.is_authenticated:
        return False
    # I also grant access to staff and superusers so admins can always get through
    if user.is_superuser or user.is_staff:
        return True
    return user.tier in {'PRO', 'PRO_PLUS', 'MANAGER', 'ADMIN'}


def has_pro_plus_access(user):
    """Shared rule for Pro+ only capabilities."""
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return user.tier in {'PRO_PLUS', 'MANAGER', 'ADMIN'}


def manager_required(view_func):
    """Restrict a view to inventory admins/managers."""
    @wraps(view_func)  # I use wraps so the original function name and docstring are preserved
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and (
            request.user.tier in {'MANAGER', 'ADMIN'} or request.user.is_staff or request.user.is_superuser
        ):
            return view_func(request, *args, **kwargs)
        # If none of the conditions pass, I raise a 403 instead of redirecting
        raise PermissionDenied
    return _wrapped_view


def purchase_access_required(view_func):
    """Allow purchase/cart actions only for paid/member users.
    Visitors can browse and view pricing but cannot purchase."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # If the user isn't logged in at all, I send them to the login page
        if not request.user.is_authenticated:
            messages.info(request, "Create an account to start building your crate.")
            return redirect('login')

        # If they're logged in but still on the free Visitor tier, I send them to the pricing page
        if not has_pro_access(request.user):
            messages.info(request, "Upgrade from Visitor to Pro to purchase records.")
            return redirect('pricing')

        return view_func(request, *args, **kwargs)
    return _wrapped_view
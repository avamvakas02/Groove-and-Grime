from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import redirect


def has_pro_access(user):
    """Shared rule for Pro-only member capabilities."""
    if not user.is_authenticated:
        return False
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
    """
    Restrict a view to inventory admins/managers.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Grant access to MANAGER/ADMIN tiers, Django staff admins, or superusers.
        if request.user.is_authenticated and (
            request.user.tier in {'MANAGER', 'ADMIN'} or request.user.is_staff or request.user.is_superuser
        ):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped_view 


def purchase_access_required(view_func):
    """
    Allow purchase/cart actions only for paid/member users.
    Visitors can browse and view pricing but cannot purchase.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Create an account to start building your crate.")
            return redirect('login')

        if not has_pro_access(request.user):
            messages.info(request, "Upgrade from Visitor to Pro to purchase records.")
            return redirect('pricing')

        return view_func(request, *args, **kwargs)
    return _wrapped_view
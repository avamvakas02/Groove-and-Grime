from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Count
from django.contrib.auth import login
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from .models import VinylRecord, Category, User
from .forms import RegisterForm, VinylRecordForm, MembershipPaymentForm
from .cart import Cart
from .decorators import manager_required, purchase_access_required, has_pro_plus_access

def _cart_totals_context(request, cart):
    """Build cart totals and discount metadata for template/JSON responses."""
    subtotal = cart.get_total_price()
    discount_rate = Decimal('0.00')
    bulk_discount_rate = Decimal('0.00')

    if request.user.is_authenticated:
        if request.user.tier == 'PRO':
            discount_rate = Decimal('0.10')
        elif request.user.tier == 'PRO_PLUS':
            discount_rate = Decimal('0.20')
            # Keep this simple: Pro+ gets an extra 5% on 10+ items.
            if len(cart) >= 10:
                bulk_discount_rate = Decimal('0.05')

    discount_rate += bulk_discount_rate
    discount_amount = subtotal * discount_rate
    total_after_discount = subtotal - discount_amount
    discount_percent = int(discount_rate * 100)
    return {
        'subtotal': subtotal,
        'discount_rate': discount_rate,
        'discount_percent': discount_percent,
        'discount_amount': discount_amount,
        'total_after_discount': total_after_discount,
    }


# --- 1. Storefront views ---

def home(request):
    """Landing page with hero sections and quick links."""
    top_artists = (
        VinylRecord.objects
        .values('artist')
        .annotate(record_count=Count('id'))
        .order_by('-record_count', 'artist')[:6]
    )
    top_labels = (
        VinylRecord.objects
        .values('label')
        .annotate(record_count=Count('id'))
        .order_by('-record_count', 'label')[:6]
    )
    return render(request, 'home.html', {
        'top_artists': top_artists,
        'top_labels': top_labels,
    })

def collection(request):
    """Record catalogue with search and tier-based visibility."""
    query = request.GET.get('q')
    categories = Category.objects.all()
    
    # If a search query exists, search title/artist/category.
    if query:
        records = VinylRecord.objects.filter(
            Q(title__icontains=query) | 
            Q(artist__icontains=query) | 
            Q(category__name__icontains=query) |
            Q(label__icontains=query)
        ).distinct()
    else:
        records = VinylRecord.objects.all()

    # Hide exclusive records for guests and lower tiers.
    if not has_pro_plus_access(request.user):
        records = records.filter(is_exclusive=False)

    context = {
        'records': records.order_by('-created_at'), 
        'categories': categories, 
        'query': query
    }
    return render(request, 'collection.html', context)


def artists(request):
    """Public index of artists with record counts."""
    artist_rows = (
        VinylRecord.objects
        .values('artist')
        .annotate(record_count=Count('id'))
        .order_by('artist')
    )
    return render(request, 'artists.html', {'artists': artist_rows})


def artist_detail(request, artist_name):
    """Public artist page listing all records by artist."""
    records = VinylRecord.objects.filter(artist=artist_name).order_by('-created_at')
    return render(request, 'artist_detail.html', {
        'artist_name': artist_name,
        'records': records,
    })


def labels(request):
    """Public index of labels with record counts."""
    label_rows = (
        VinylRecord.objects
        .values('label')
        .annotate(record_count=Count('id'))
        .order_by('label')
    )
    return render(request, 'labels.html', {'labels': label_rows})


def label_detail(request, label_name):
    """Public label page listing all records from a label."""
    records = VinylRecord.objects.filter(label=label_name).order_by('-created_at')
    return render(request, 'label_detail.html', {
        'label_name': label_name,
        'records': records,
    })


def editorial(request):
    """Public editorial/blog page with scene updates and mixes."""
    posts = [
        {
            'title': 'Athens Afterhours: April Deep Cuts',
            'category': 'Mixes',
            'summary': 'A late-night selection of deep house and minimal records currently rotating in local booths.',
        },
        {
            'title': 'Label Watch: Underground Presses to Follow',
            'category': 'Scene News',
            'summary': 'Three independent labels pushing gritty club sounds and limited wax releases this month.',
        },
        {
            'title': 'Staff Picks: Warm-Up Builders',
            'category': 'Staff Picks',
            'summary': 'The Groove & Grime team shares opening-hour records with long blends and steady momentum.',
        },
    ]
    return render(request, 'editorial.html', {'posts': posts})


# --- 2. Authentication ---

def register(request):
    """Create a new account and log the user in immediately."""
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to the club, {user.username}!")
            return redirect("home")
    else:
        form = RegisterForm()
    return render(request, "register.html", {"form": form})


# --- 3. Cart ("Crate") ---

@purchase_access_required
def cart_detail(request):
    """Display all items currently stored in session cart."""
    cart = Cart(request)
    totals = _cart_totals_context(request, cart)

    return render(request, 'cart_detail.html', {
        'cart': cart,
        **totals,
    })

@purchase_access_required
def cart_add(request, record_id):
    """Add one record to the session cart."""
    cart = Cart(request)
    record = get_object_or_404(VinylRecord, id=record_id)
    if record.is_exclusive and not has_pro_plus_access(request.user):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'ok': False,
                'redirect_url': '/pricing/',
                'message': "This release is Pro+ only. Upgrade to unlock it.",
            }, status=403)
        messages.info(request, "This release is Pro+ only. Upgrade to unlock it.")
        return redirect('pricing')
    cart.add(record=record)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'ok': True,
            'item_count': len(cart),
            'record_title': record.title,
        })
    messages.success(request, f"'{record.title}' added to your crate.")
    return redirect(request.META.get('HTTP_REFERER', 'collection'))

@require_POST
@purchase_access_required
def cart_remove(request, record_id):
    """Remove a record from the session cart."""
    cart = Cart(request)
    record = get_object_or_404(VinylRecord, id=record_id)
    cart.remove(record)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        totals = _cart_totals_context(request, cart)
        return JsonResponse({
            'ok': True,
            'record_id': record.id,
            'quantity': 0,
            'line_total': "0.00",
            'item_count': len(cart),
            'subtotal': f"{totals['subtotal']:.2f}",
            'discount_amount': f"{totals['discount_amount']:.2f}",
            'discount_percent': totals['discount_percent'],
            'total_after_discount': f"{totals['total_after_discount']:.2f}",
        })
    return redirect('cart_detail')


@require_POST
@purchase_access_required
def cart_update_quantity(request, record_id):
    """Increase or decrease quantity of a specific cart item."""
    cart = Cart(request)
    record = get_object_or_404(VinylRecord, id=record_id)
    action = request.POST.get('action')

    if action == 'increase':
        cart.add(record=record, quantity=1)
    elif action == 'decrease':
        cart.add(record=record, quantity=-1)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        quantity = cart.cart.get(str(record.id), {}).get('quantity', 0)
        totals = _cart_totals_context(request, cart)
        return JsonResponse({
            'ok': True,
            'record_id': record.id,
            'quantity': quantity,
            'line_total': f"{(Decimal(record.price) * quantity):.2f}",
            'item_count': len(cart),
            'subtotal': f"{totals['subtotal']:.2f}",
            'discount_amount': f"{totals['discount_amount']:.2f}",
            'discount_percent': totals['discount_percent'],
            'total_after_discount': f"{totals['total_after_discount']:.2f}",
        })

    return redirect('cart_detail')


# --- 4. Manager dashboard (front-end management) ---

@manager_required
def manager_dashboard(request):
    """List all records in a manager-only dashboard."""
    records = VinylRecord.objects.all().order_by('-created_at')
    return render(request, 'manager/dashboard.html', {'records': records})

@manager_required
def add_vinyl(request):
    """Create a new record from the manager dashboard."""
    if request.method == "POST":
        form = VinylRecordForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "New vinyl successfully added to inventory.")
            return redirect('manager_dashboard')
    else:
        form = VinylRecordForm()
    return render(request, 'manager/vinyl_form.html', {
        'form': form, 
        'title': 'Add New Vinyl'
    })

@manager_required
def delete_vinyl(request, record_id):
    """Delete a record from inventory."""
    record = get_object_or_404(VinylRecord, id=record_id)
    record.delete()
    messages.warning(request, f"'{record.title}' has been removed from the catalog.")
    return redirect('manager_dashboard')


@manager_required
@require_POST
def update_stock(request, record_id):
    """Increase/decrease stock from dashboard controls."""
    record = get_object_or_404(VinylRecord, id=record_id)
    action = request.POST.get('action')

    if action == 'increase':
        record.stock += 1
        record.save(update_fields=['stock'])
        messages.success(request, f"Stock increased for '{record.title}'.")
    elif action == 'decrease':
        if record.stock > 0:
            record.stock -= 1
            record.save(update_fields=['stock'])
            messages.info(request, f"Stock decreased for '{record.title}'.")
        else:
            messages.warning(request, f"'{record.title}' is already at zero stock.")
    else:
        messages.error(request, "Invalid stock action.")

    return redirect('manager_dashboard')

def pricing(request):
    """Display static membership tiers and benefits page."""
    return render(request, 'pricing.html', {
        'pro_privileges': User.PRO_PRIVILEGES,
        'pro_plus_privileges': User.PRO_PLUS_PRIVILEGES,
    })


@require_POST
@login_required
def update_membership(request):
    """Update logged-in user's membership tier from pricing page."""
    tier = request.POST.get('tier')
    allowed_tiers = {'VISITOR', 'PRO', 'PRO_PLUS'}

    if tier not in allowed_tiers:
        messages.error(request, "Invalid membership tier selected.")
        return redirect('pricing')

    if request.user.tier == tier:
        messages.info(request, "You are already on this membership tier.")
        return redirect('pricing')

    request.user.tier = tier
    request.user.save(update_fields=['tier'])
    messages.success(request, f"Membership updated to {request.user.get_tier_display()}.")
    return redirect('pricing')


@login_required
def change_membership(request, tier):
    """Collect card details before updating user's membership tier."""
    allowed_tiers = {'PRO', 'PRO_PLUS'}
    if tier not in allowed_tiers:
        messages.error(request, "Invalid membership tier selected.")
        return redirect('pricing')

    if request.user.tier == tier:
        messages.info(request, "You are already on this membership tier.")
        return redirect('pricing')

    if request.method == 'POST':
        form = MembershipPaymentForm(request.POST)
        if form.is_valid():
            request.user.tier = tier
            request.user.save(update_fields=['tier'])
            messages.success(request, f"Membership updated to {request.user.get_tier_display()}.")
            return redirect('pricing')
    else:
        form = MembershipPaymentForm()

    return render(request, 'membership_checkout.html', {
        'form': form,
        'target_tier': tier,
        'target_tier_label': dict(User.TIER_CHOICES).get(tier, tier),
    })
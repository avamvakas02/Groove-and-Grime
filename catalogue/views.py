from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Count, Avg
from django.contrib.auth import login
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from .models import VinylRecord, Category, User, Review, WishlistItem
from .forms import (
    RegisterForm,
    VinylRecordForm,
    MembershipPaymentForm,
    ProfileUpdateForm,
)
from .cart import Cart
from .decorators import manager_required, purchase_access_required, has_pro_plus_access


def _visibility_filtered_records(user):
    """Base record queryset respecting Pro+ exclusive visibility."""
    records = VinylRecord.objects.all()
    if not has_pro_plus_access(user):
        records = records.filter(is_exclusive=False)
    return records


def _build_recommendations(user, seed_records, base_records, limit=6):
    """
    Recommend records using content similarity and optional user-history boost.
    Similarity uses category/artist/label overlap.
    History boost uses the user's high-rated (4-5 stars) records.
    """
    candidates = list(base_records.exclude(id__in=[record.id for record in seed_records]))
    if not candidates:
        return []

    seed_categories = {record.category_id for record in seed_records}
    seed_artists = {record.artist for record in seed_records}
    seed_labels = {record.label for record in seed_records}

    preferred_categories = set()
    preferred_artists = set()
    preferred_labels = set()
    if user.is_authenticated:
        high_rated_reviews = (
            Review.objects
            .filter(user=user, rating__gte=4)
            .select_related('record')
        )
        preferred_categories = {review.record.category_id for review in high_rated_reviews}
        preferred_artists = {review.record.artist for review in high_rated_reviews}
        preferred_labels = {review.record.label for review in high_rated_reviews}

    scored = []
    for record in candidates:
        score = 0
        if record.category_id in seed_categories:
            score += 3
        if record.artist in seed_artists:
            score += 2
        if record.label in seed_labels:
            score += 1

        # Boost from user's high-rated history.
        if record.category_id in preferred_categories:
            score += 4
        if record.artist in preferred_artists:
            score += 3
        if record.label in preferred_labels:
            score += 2

        if score > 0:
            scored.append((score, record))

    scored.sort(key=lambda row: (-row[0], -row[1].created_at.timestamp()))
    return [row[1] for row in scored[:limit]]


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
    query = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '').strip()
    selected_label = request.GET.get('label', '').strip()
    selected_condition = request.GET.get('condition', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    categories = Category.objects.all()
    labels = (
        VinylRecord.objects
        .exclude(label__isnull=True)
        .exclude(label__exact='')
        .values_list('label', flat=True)
        .distinct()
        .order_by('label')
    )
    conditions = [choice[0] for choice in VinylRecord.CONDITION_CHOICES]

    records = _visibility_filtered_records(request.user)

    # Full-text-ish search on key record descriptors.
    if query:
        records = records.filter(
            Q(title__icontains=query) |
            Q(artist__icontains=query) |
            Q(category__name__icontains=query) |
            Q(label__icontains=query)
        )

    # Advanced filters.
    if selected_category:
        records = records.filter(category_id=selected_category)
    if selected_label:
        records = records.filter(label=selected_label)
    if selected_condition:
        records = records.filter(condition=selected_condition)
    if min_price:
        try:
            records = records.filter(price__gte=Decimal(min_price))
        except Exception:
            messages.warning(request, "Invalid minimum price filter ignored.")
    if max_price:
        try:
            records = records.filter(price__lte=Decimal(max_price))
        except Exception:
            messages.warning(request, "Invalid maximum price filter ignored.")

    records = records.distinct()

    records_with_stats = list(records.annotate(
        average_rating=Avg('reviews__rating'),
        review_count=Count('reviews'),
    ).order_by('-created_at'))

    if request.user.is_authenticated:
        review_map = {
            review.record_id: review
            for review in Review.objects.filter(user=request.user, record__in=records)
        }
        wishlisted_record_ids = set(
            WishlistItem.objects
            .filter(user=request.user, record__in=records)
            .values_list('record_id', flat=True)
        )
    else:
        review_map = {}
        wishlisted_record_ids = set()

    for record in records_with_stats:
        user_review = review_map.get(record.id)
        record.current_user_rating = user_review.rating if user_review else 0
        record.current_user_comment = user_review.comment if user_review else ''
        record.is_wishlisted = record.id in wishlisted_record_ids

    # Seed recommender with visible filtered records first, fallback to latest records.
    seed_records = records_with_stats[:8]
    if not seed_records:
        seed_records = list(_visibility_filtered_records(request.user).order_by('-created_at')[:8])
    recommended_records = _build_recommendations(
        request.user,
        seed_records=seed_records,
        base_records=_visibility_filtered_records(request.user),
        limit=6,
    )

    context = {
        'records': records_with_stats,
        'record_count': len(records_with_stats),
        'recommended_records': recommended_records,
        'categories': categories,
        'labels': labels,
        'conditions': conditions,
        'query': query,
        'selected_category': selected_category,
        'selected_label': selected_label,
        'selected_condition': selected_condition,
        'min_price': min_price,
        'max_price': max_price,
    }
    return render(request, 'collection.html', context)


@require_POST
@login_required
def save_review(request, record_id):
    """Create or update a logged-in user's star rating/review via AJAX."""
    record = get_object_or_404(VinylRecord, id=record_id)
    try:
        rating = int(request.POST.get('rating', '0'))
    except ValueError:
        return JsonResponse({'ok': False, 'message': 'Invalid rating value.'}, status=400)

    comment = request.POST.get('comment', '').strip()
    if rating < 1 or rating > 5:
        return JsonResponse({'ok': False, 'message': 'Rating must be between 1 and 5.'}, status=400)

    review, _created = Review.objects.update_or_create(
        user=request.user,
        record=record,
        defaults={
            'rating': rating,
            'comment': comment,
        },
    )

    aggregate = Review.objects.filter(record=record).aggregate(
        average_rating=Avg('rating'),
        review_count=Count('id'),
    )
    return JsonResponse({
        'ok': True,
        'message': 'Your review has been saved.',
        'record_id': record.id,
        'user_rating': review.rating,
        'user_comment': review.comment,
        'average_rating': round(aggregate['average_rating'] or 0, 2),
        'review_count': aggregate['review_count'] or 0,
    })


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


@login_required
def profile(request):
    """Display current user profile details."""
    return render(request, 'profile.html')


@login_required
def wishlist(request):
    """Display wishlist page entry point for logged-in users."""
    wishlisted_records = list(
        _visibility_filtered_records(request.user)
        .filter(wishlisted_by__user=request.user)
        .annotate(
            average_rating=Avg('reviews__rating'),
            review_count=Count('reviews'),
        )
        .distinct()
        .order_by('-wishlisted_by__created_at')
    )

    review_map = {
        review.record_id: review
        for review in Review.objects.filter(user=request.user, record__in=wishlisted_records)
    }

    for record in wishlisted_records:
        user_review = review_map.get(record.id)
        record.current_user_rating = user_review.rating if user_review else 0
        record.current_user_comment = user_review.comment if user_review else ''
        record.is_wishlisted = True

    return render(request, 'wishlist.html', {'records': wishlisted_records})


@login_required
def my_reviews(request):
    """Display all reviews submitted by the current user."""
    user_reviews = (
        Review.objects
        .filter(user=request.user)
        .select_related('record')
        .order_by('-updated_at')
    )
    return render(request, 'my_reviews.html', {'user_reviews': user_reviews})


@login_required
@require_POST
def wishlist_add(request, record_id):
    """Add a record to the current user's wishlist."""
    record = get_object_or_404(VinylRecord, id=record_id)
    WishlistItem.objects.get_or_create(user=request.user, record=record)
    messages.success(request, f"'{record.title}' added to your wishlist.")
    return redirect(request.POST.get('next') or 'collection')


@login_required
@require_POST
def wishlist_remove(request, record_id):
    """Remove a record from the current user's wishlist."""
    record = get_object_or_404(VinylRecord, id=record_id)
    WishlistItem.objects.filter(user=request.user, record=record).delete()
    messages.info(request, f"'{record.title}' removed from your wishlist.")
    return redirect(request.POST.get('next') or 'wishlist')


@login_required
def faq(request):
    """Display frequently asked questions page for account/store topics."""
    return render(request, 'faq.html')


@login_required
def edit_profile(request):
    """Update current user profile details."""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'profile.html', {'form': form})
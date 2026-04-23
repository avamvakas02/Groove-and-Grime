# models.py — Defines all the database models for Groove & Grime
# I have four main models here: User, Category, VinylRecord, Review, and WishlistItem

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.templatetags.static import static
from django.contrib.staticfiles import finders
import os


# --- Custom user model ---

class User(AbstractUser):
    """Application user with a membership tier used for access and pricing."""
    TIER_CHOICES = (
        ('VISITOR', 'Visitor'),
        ('PRO', 'Pro'),
        ('PRO_PLUS', 'Pro+'),
        ('MANAGER', 'Manager'),
        ('ADMIN', 'Admin'),
    )

    tier = models.CharField(
        max_length=10,
        choices=TIER_CHOICES,
        default='VISITOR',
        help_text="Determines user access level and exclusive discounts."
    )

    # I store these as class-level tuples so I can reference them in templates via context processors
    PRO_PRIVILEGES = (
        "Purchase records (single and bulk orders)",
        "Full-length previews before buying",
        "Wishlist / wantlist to save records for later",
        "Back-in-stock notifications for specific records",
        "Order history and downloadable invoices",
        "Pre-order access for upcoming releases",
        "Basic recommendations based on purchase history",
        "Rating and reviewing records",
        "Members-only sales and discounts",
        "Saved shipping addresses",
        "Follow artists or labels and get new-stock notifications",
    )
    PRO_PLUS_PRIVILEGES = (
        "Early access to new arrivals before general availability (24-48h window)",
        "Reserve / hold records for 48h without immediate purchase",
        "Exclusive and limited-edition releases visible and purchasable only at this tier",
        "Advanced filtering by key, BPM range, pressing country, and matrix number",
        "Discounted shipping or free-shipping thresholds",
        "Priority customer support",
        "Personal crate with a curated public profile showcase",
        "Collection tracker to log owned records and avoid duplicates",
        "Advanced recommendations with deeper ML/editorial matching",
        "Bulk discount pricing for larger orders (e.g. 10+ records)",
        "Direct label drops with exclusive batch access",
        "Monthly personalized digest of new arrivals based on taste profile",
    )

    def __str__(self):
        return f"{self.username} ({self.tier_label})"

    @property
    def tier_label(self):
        """Returns a friendly tier label, giving superusers the Admin label explicitly."""
        if self.is_superuser or self.tier == 'ADMIN':
            return "Admin"
        return self.get_tier_display()

    @property
    def is_pro_member(self):
        """True when the account has Pro-level access or higher."""
        if self.is_superuser or self.is_staff:
            return True
        return self.tier in {'PRO', 'PRO_PLUS', 'MANAGER', 'ADMIN'}

    @property
    def is_pro_plus_member(self):
        """True when the account has Pro+ access or higher."""
        if self.is_superuser or self.is_staff:
            return True
        return self.tier in {'PRO_PLUS', 'MANAGER', 'ADMIN'}


# --- Product category model ---

class Category(models.Model):
    """Groups records into genres/collections used for filtering in the collection view."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"  # Fixes the default "Categorys" label in Django admin

    def __str__(self):
        return self.name


# --- Vinyl inventory model ---

class VinylRecord(models.Model):
    STATIC_VINYL_CATEGORY_DIRS = (
        'vinyls/categories/deep-house',
        'vinyls/categories/chicago-jackin',
        'vinyls/categories/acid-house',
        'vinyls/categories/tech-house',
    )

    """Main product model for records displayed in the collection, cart, and wishlist."""
    CONDITION_CHOICES = (
        ('Mint', 'Mint (M)'),
        ('Near Mint', 'Near Mint (NM)'),
        ('Very Good', 'Very Good (VG+)'),
        ('Good', 'Good (G)'),
    )

    title = models.CharField(max_length=200)
    artist = models.CharField(max_length=200)
    label = models.CharField(max_length=200, default='Independent')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='records')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='Mint')
    description = models.TextField()
    image = models.ImageField(upload_to='records/', blank=True, null=True)
    stock = models.PositiveIntegerField(default=1)

    # If this is checked, the record is hidden from Visitor and Pro users in the collection view
    is_exclusive = models.BooleanField(
        default=False,
        help_text="If checked, only Pro+ and Managers can see this record."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.artist} - {self.title}"

    @property
    def image_display_url(self):
        """Return a safe image URL for both media uploads and static seed paths."""
        if not self.image:
            return static('images/limited-edition.png')

        image_name = (self.image.name or '').strip()
        if image_name.startswith(('vinyls/', 'images/')):
            # Direct static path first.
            if finders.find(image_name):
                return static(image_name)

            # Seed data stores "vinyls/<file>" while assets live in category subfolders.
            filename = os.path.basename(image_name)
            for category_dir in self.STATIC_VINYL_CATEGORY_DIRS:
                candidate = f"{category_dir}/{filename}"
                if finders.find(candidate):
                    return static(candidate)

        try:
            return self.image.url
        except Exception:
            return static('images/limited-edition.png')


# --- Review model ---

class Review(models.Model):
    """Stores a user's star rating and optional comment for a vinyl record."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    record = models.ForeignKey(VinylRecord, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # I enforce one review per user per record at the database level
            models.UniqueConstraint(fields=['user', 'record'], name='unique_user_record_review'),
            # I also make sure ratings can only be between 1 and 5
            models.CheckConstraint(condition=models.Q(rating__gte=1) & models.Q(rating__lte=5), name='rating_between_1_and_5'),
        ]
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username} rated {self.record} ({self.rating}/5)"


# --- Wishlist model ---

class WishlistItem(models.Model):
    """Stores records a user has saved to their wishlist for later."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    record = models.ForeignKey(VinylRecord, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # I prevent the same record from being added to the same user's wishlist twice
            models.UniqueConstraint(fields=['user', 'record'], name='unique_user_record_wishlist_item'),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} wishlisted {self.record}"
from django.db import models
from django.contrib.auth.models import AbstractUser

# --- Custom user model ---
# We extend Django's default user so every account has a membership tier.

class User(AbstractUser):
    """Application user with a membership tier used for access and pricing."""
    TIER_CHOICES = (
        ('VISITOR', 'Visitor'),
        ('PRO', 'Pro'),
        ('PRO_PLUS', 'Pro+'),
        ('MANAGER', 'Manager'),
    )
    
    tier = models.CharField(
        max_length=10, 
        choices=TIER_CHOICES, 
        default='VISITOR',
        help_text="Determines user access level and exclusive discounts."
    )

    # Core perks that define the Pro experience on the storefront.
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
        """Show username and tier in admin/list displays."""
        return f"{self.username} ({self.get_tier_display()})"

    @property
    def is_pro_member(self):
        """
        True when the account has Pro-level storefront access.
        Pro+ and Manager include all Pro privileges.
        """
        if self.is_superuser or self.is_staff:
            return True
        return self.tier in {'PRO', 'PRO_PLUS', 'MANAGER'}

    @property
    def is_pro_plus_member(self):
        """True when the account has top-tier Pro+ storefront access."""
        if self.is_superuser or self.is_staff:
            return True
        return self.tier in {'PRO_PLUS', 'MANAGER'}


# --- Product category model ---

class Category(models.Model):
    """Groups records into genres/collections used in filtering."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        """Readable category name in admin and templates."""
        return self.name


# --- Vinyl inventory model ---

class VinylRecord(models.Model):
    """Main product model for records displayed in collection and cart."""
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
    
    # Exclusive records are hidden from lower tiers in collection view logic.
    is_exclusive = models.BooleanField(
        default=False, 
        help_text="If checked, only Pro+ and Managers can see this record."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Readable record label used in admin and debugging."""
        return f"{self.artist} - {self.title}"


class Review(models.Model):
    """User rating/review for a vinyl record."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    record = models.ForeignKey(VinylRecord, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'record'], name='unique_user_record_review'),
            models.CheckConstraint(condition=models.Q(rating__gte=1) & models.Q(rating__lte=5), name='rating_between_1_and_5'),
        ]
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username} rated {self.record} ({self.rating}/5)"
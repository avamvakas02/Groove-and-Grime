
from decimal import Decimal
from .models import VinylRecord


class Cart:
    """Session-backed shopping cart used across collection and checkout pages."""

    def __init__(self, request):
        """Load existing session cart or initialize an empty one."""
        self.session = request.session
        cart = self.session.get('cart')
        # If there's no cart in the session yet, I create an empty dict and store it
        if not cart:
            cart = self.session['cart'] = {}
        self.cart = cart

    def add(self, record, quantity=1, override_quantity=False):
        """Add/increment a record and cap quantity at available stock."""
        record_id = str(record.id)
        # I use a string key because Django sessions serialize to JSON, which requires string keys
        if record_id not in self.cart:
            self.cart[record_id] = {'price': str(record.price), 'quantity': 0}

        if override_quantity:
            new_quantity = quantity
        else:
            new_quantity = self.cart[record_id]['quantity'] + quantity

        if new_quantity <= 0:
            del self.cart[record_id]
        else:
            # I use min() to make sure the quantity never exceeds what's actually in stock
            self.cart[record_id]['quantity'] = min(new_quantity, record.stock)
        self.save()

    def remove(self, record):
        """Remove record from the cart session payload."""
        record_id = str(record.id)
        if record_id in self.cart:
            del self.cart[record_id]
            self.save()

    def save(self):
        """Mark session as modified so Django persists cart changes."""
        # Without this, Django won't always detect that the session data changed and may not save it
        self.session.modified = True

    def __iter__(self):
        """Yield enriched cart items with record object and total line price."""
        record_ids = self.cart.keys()
        # I fetch all the records in one query instead of querying inside the loop
        records = VinylRecord.objects.filter(id__in=record_ids)
        cart = self.cart.copy()
        for record in records:
            cart[str(record.id)]['record'] = record
        for item in cart.values():
            item['total_price'] = Decimal(item['price']) * item['quantity']
            yield item

    def get_total_price(self):
        """Return the total cart value."""
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def __len__(self):
        """Return the number of units in cart."""
        # I count total units rather than unique items so a qty of 3 counts as 3
        return sum(item['quantity'] for item in self.cart.values())
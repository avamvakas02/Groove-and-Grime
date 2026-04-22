from decimal import Decimal
from .models import VinylRecord


class Cart:
    """Session-backed shopping cart used across collection and checkout pages."""

    def __init__(self, request):
        """Load existing session cart or initialize an empty one."""
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            cart = self.session['cart'] = {}
        self.cart = cart

    def add(self, record, quantity=1, override_quantity=False):
        """Add/increment a record and cap quantity at available stock."""
        record_id = str(record.id)
        if record_id not in self.cart:
            self.cart[record_id] = {'price': str(record.price), 'quantity': 0}

        if override_quantity:
            new_quantity = quantity
        else:
            new_quantity = self.cart[record_id]['quantity'] + quantity

        if new_quantity <= 0:
            del self.cart[record_id]
        else:
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
        self.session.modified = True

    def __iter__(self):
        """Yield enriched cart items with record object and total line price."""
        record_ids = self.cart.keys()
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
        return sum(item['quantity'] for item in self.cart.values())
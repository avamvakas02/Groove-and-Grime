# forms.py — All the forms used across the site, from registration to checkout

from datetime import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from .models import User, VinylRecord


# --- 1. User registration form ---

class RegisterForm(UserCreationForm):
    """
    Custom registration form built on top of Django's UserCreationForm.
    I collect email and force new accounts to start as VISITOR.
    """
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control bg-dark text-white border-secondary',
        'placeholder': 'email@example.com'
    }))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # I style the inherited username field here since I can't set its widget attrs in Meta
        self.fields['username'].widget.attrs.update({
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'Choose a username'
        })

    def save(self, commit=True):
        """Persist user and enforce default tier for new registrations."""
        user = super().save(commit=False)
        user.tier = 'VISITOR'  # Every new account starts as Visitor no matter what
        if commit:
            user.save()
        return user


# --- 2. Manager inventory form ---

class VinylRecordForm(forms.ModelForm):
    """Form used by managers to create or edit vinyl records in the inventory."""
    class Meta:
        model = VinylRecord
        fields = [
            'title', 'artist', 'label', 'category', 'price',
            'condition', 'description', 'image', 'stock', 'is_exclusive'
        ]
        # I define all widgets here so every input matches the dark Bootstrap theme
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-secondary'}),
            'artist': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-secondary'}),
            'label': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-secondary'}),
            'category': forms.Select(attrs={'class': 'form-select bg-dark text-white border-secondary'}),
            'price': forms.NumberInput(attrs={'class': 'form-control bg-dark text-white border-secondary'}),
            'condition': forms.Select(attrs={'class': 'form-select bg-dark text-white border-secondary'}),
            'description': forms.Textarea(attrs={'class': 'form-control bg-dark text-white border-secondary', 'rows': 4}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control bg-dark text-white border-secondary'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control bg-dark text-white border-secondary'}),
            'is_exclusive': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # I override the label to make it obvious what "exclusive" means in this context
        self.fields['is_exclusive'].label = "Pro+ Exclusive (Only visible to higher tiers)"


# --- 3. Membership upgrade payment form ---

class MembershipPaymentForm(forms.Form):
    """Collect basic card details before upgrading membership."""
    cardholder_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'Cardholder Name',
            'autocomplete': 'cc-name',
        }),
    )
    card_number = forms.CharField(
        max_length=19,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': '1234 5678 9012 3456',
            'autocomplete': 'cc-number',
            'inputmode': 'numeric',
        }),
    )
    expiry_date = forms.CharField(
        max_length=5,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'MM/YY',
            'autocomplete': 'cc-exp',
        }),
    )
    cvv = forms.CharField(
        max_length=4,
        # I use PasswordInput so the CVV is masked while the user types it
        widget=forms.PasswordInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'CVV',
            'autocomplete': 'cc-csc',
            'inputmode': 'numeric',
        }),
    )

    def clean_card_number(self):
        raw = self.cleaned_data['card_number']
        # I strip out any spaces or dashes the user might have typed
        digits_only = ''.join(ch for ch in raw if ch.isdigit())
        if len(digits_only) < 13 or len(digits_only) > 19:
            raise ValidationError("Please enter a valid card number.")
        return digits_only

    def clean_expiry_date(self):
        raw = self.cleaned_data['expiry_date'].strip()
        # I extract only the digits so the format doesn't matter as much on input
        digits_only = ''.join(ch for ch in raw if ch.isdigit())
        if len(digits_only) != 4:
            raise ValidationError("Expiry date must be in MM/YY format.")
        month = digits_only[:2]
        year = digits_only[2:]
        month_num = int(month)
        if month_num < 1 or month_num > 12:
            raise ValidationError("Please enter a valid expiry month.")
        return f"{month}/{year}"  # I always return in a consistent MM/YY format

    def clean_cvv(self):
        raw = self.cleaned_data['cvv'].strip()
        if not raw.isdigit() or len(raw) not in (3, 4):
            raise ValidationError("Please enter a valid CVV.")
        return raw


# --- 4. Cart checkout form ---

class CartCheckoutForm(forms.Form):
    """Collect shipping and payment details at checkout."""
    full_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'Full name',
            'autocomplete': 'name',
        }),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
        }),
    )
    address_line_1 = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'Street and number',
            'autocomplete': 'address-line1',
        }),
    )
    city = forms.CharField(
        max_length=60,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'City',
            'autocomplete': 'address-level2',
        }),
    )
    postal_code = forms.CharField(
        max_length=12,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'Postal code',
            'autocomplete': 'postal-code',
        }),
    )
    card_number = forms.CharField(
        max_length=19,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': '1234 5678 9012 3456',
            'autocomplete': 'cc-number',
            'inputmode': 'numeric',
        }),
    )
    expiry_date = forms.CharField(
        max_length=5,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'MM/YY',
            'autocomplete': 'cc-exp',
        }),
    )
    cvv = forms.CharField(
        max_length=4,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'CVV',
            'autocomplete': 'cc-csc',
            'inputmode': 'numeric',
        }),
    )

    def clean_full_name(self):
        value = self.cleaned_data['full_name'].strip()
        # I require at least two words so the user can't just submit a first name
        if len(value.split()) < 2:
            raise ValidationError("Please enter both first and last name.")
        return value

    def clean_postal_code(self):
        value = self.cleaned_data['postal_code'].strip()
        normalized = value.replace(' ', '')
        if len(normalized) < 4 or not any(ch.isdigit() for ch in normalized):
            raise ValidationError("Please enter a valid postal code.")
        return value

    def clean_card_number(self):
        raw = self.cleaned_data['card_number']
        digits_only = ''.join(ch for ch in raw if ch.isdigit())
        if len(digits_only) < 13 or len(digits_only) > 19:
            raise ValidationError("Please enter a valid card number.")
        return digits_only

    def clean_expiry_date(self):
        raw = self.cleaned_data['expiry_date'].strip()
        digits_only = ''.join(ch for ch in raw if ch.isdigit())
        if len(digits_only) != 4:
            raise ValidationError("Expiry date must be in MM/YY format.")
        month = digits_only[:2]
        year = digits_only[2:]
        month_num = int(month)
        if month_num < 1 or month_num > 12:
            raise ValidationError("Please enter a valid expiry month.")
        # I also check against today's date to catch expired cards before the order goes through
        current = datetime.now()
        expiry_year = 2000 + int(year)
        if expiry_year < current.year or (expiry_year == current.year and month_num < current.month):
            raise ValidationError("This card appears to be expired.")
        return f"{month}/{year}"

    def clean_cvv(self):
        raw = self.cleaned_data['cvv'].strip()
        if not raw.isdigit() or len(raw) not in (3, 4):
            raise ValidationError("Please enter a valid CVV.")
        return raw


# --- 5. Profile update form ---

class ProfileUpdateForm(forms.ModelForm):
    """Allow users to edit basic profile fields."""
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control bg-dark text-white border-secondary',
                'placeholder': 'Username',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control bg-dark text-white border-secondary',
                'placeholder': 'email@example.com',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control bg-dark text-white border-secondary',
                'placeholder': 'First name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control bg-dark text-white border-secondary',
                'placeholder': 'Last name',
            }),
        }


# --- 6. Public contact form ---

class ContactForm(forms.Form):
    """Public contact form for store questions and collaboration inquiries."""
    full_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'Your full name',
        }),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'you@example.com',
        }),
    )
    subject = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'What is this about?',
        }),
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'rows': 5,
            'placeholder': 'Tell us how we can help.',
        }),
    )
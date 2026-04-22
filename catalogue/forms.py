from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from .models import User, VinylRecord

# --- 1. User registration form ---

class RegisterForm(UserCreationForm):
    """
    Custom registration form built on top of Django's UserCreationForm.
    We collect email and force new accounts to start as VISITOR.
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
        # Style inherited username input so it matches the site's dark theme.
        self.fields['username'].widget.attrs.update({
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'Choose a username'
        })

    def save(self, commit=True):
        """Persist user and enforce default tier for new registrations."""
        user = super().save(commit=False)
        user.tier = 'VISITOR'
        if commit:
            user.save()
        return user


# --- 2. Manager inventory form ---

class VinylRecordForm(forms.ModelForm):
    """
    Form used by managers to create or edit inventory records.
    """
    class Meta:
        model = VinylRecord
        fields = [
            'title', 'artist', 'label', 'category', 'price',
            'condition', 'description', 'image', 'stock', 'is_exclusive'
        ]
        
        # Widget classes keep UI consistent with Bootstrap + dark theme.
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
        # Friendlier label on manager dashboard form.
        self.fields['is_exclusive'].label = "Pro+ Exclusive (Only visible to higher tiers)"


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
        widget=forms.PasswordInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'CVV',
            'autocomplete': 'cc-csc',
            'inputmode': 'numeric',
        }),
    )

    def clean_card_number(self):
        raw = self.cleaned_data['card_number']
        digits_only = ''.join(ch for ch in raw if ch.isdigit())
        if len(digits_only) < 13 or len(digits_only) > 19:
            raise ValidationError("Please enter a valid card number.")
        return digits_only

    def clean_expiry_date(self):
        raw = self.cleaned_data['expiry_date'].strip()
        if len(raw) != 5 or raw[2] != '/':
            raise ValidationError("Expiry date must be in MM/YY format.")
        month, year = raw.split('/')
        if not (month.isdigit() and year.isdigit()):
            raise ValidationError("Expiry date must be in MM/YY format.")
        month_num = int(month)
        if month_num < 1 or month_num > 12:
            raise ValidationError("Please enter a valid expiry month.")
        return raw

    def clean_cvv(self):
        raw = self.cleaned_data['cvv'].strip()
        if not raw.isdigit() or len(raw) not in (3, 4):
            raise ValidationError("Please enter a valid CVV.")
        return raw
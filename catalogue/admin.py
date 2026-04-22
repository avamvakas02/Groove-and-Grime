from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Category, VinylRecord, User, Review

# Register the Custom User Model so you can edit Tiers in the Admin
class CustomUserAdmin(UserAdmin):
    model = User
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('tier',)}),
    )
    list_display = ['username', 'email', 'tier', 'is_staff']

admin.site.register(User, CustomUserAdmin)
admin.site.register(Category)
admin.site.register(VinylRecord)
admin.site.register(Review)
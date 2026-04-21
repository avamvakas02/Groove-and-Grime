from django.contrib import admin
from .models import Category, VinylRecord, Review

# This allows the Admin to manage the catalogue 
admin.site.register(Category)
admin.site.register(VinylRecord)
admin.site.register(Review)
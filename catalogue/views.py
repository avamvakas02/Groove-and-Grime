from django.shortcuts import render
from django.db.models import Q  # Essential for "OR" search queries
from .models import VinylRecord, Category

def home(request):
    """
    Renders the landing page (home.html).
    Provides a professional entry point to the web application.
    """
    return render(request, 'home.html')

def collection(request):
    """
    Renders the shop/collection page (collection.html).
    Handles the dynamic catalogue display and search functionality.
    """
    # 1. Get the search term from the URL (if the user typed something)
    query = request.GET.get('q')
    
    # 2. Get all categories to populate the Sidebar
    categories = Category.objects.all()
    
    # 3. Search Logic (Requirement 12 & 13)
    if query:
        # Filter records where the title, artist, or category contains the search term
        records = VinylRecord.objects.filter(
            Q(title__icontains=query) | 
            Q(artist__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct()
    else:
        # If no search, show everything
        records = VinylRecord.objects.all()
    
    # 4. Context dictionary to send data to the Template
    context = {
        'records': records,
        'categories': categories,
        'query': query
    }
    
    return render(request, 'collection.html', context)
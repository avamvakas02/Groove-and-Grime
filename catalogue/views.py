from django.shortcuts import render
from django.db.models import Q
from .models import VinylRecord, Category

def home(request):
    """
    Landing Page View
    This was missing, causing your 'AttributeError'
    """
    return render(request, 'home.html')

def collection(request):
    """
    Shop Page View with Search and Randomization
    """
    query = request.GET.get('q')
    categories = Category.objects.all()
    
    if query:
        # Filter by search term AND randomize
        records = VinylRecord.objects.filter(
            Q(title__icontains=query) | 
            Q(artist__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct().order_by('?')
    else:
        # Show all records in a random order
        records = VinylRecord.objects.all().order_by('?')
    
    context = {
        'records': records,
        'categories': categories,
        'query': query
    }
    
    return render(request, 'collection.html', context)
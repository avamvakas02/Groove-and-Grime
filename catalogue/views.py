from django.shortcuts import render, redirect
from django.db.models import Q
from django.contrib.auth import login
from .models import VinylRecord, Category
from .forms import RegisterForm

def home(request):
    return render(request, 'home.html')

def collection(request):
    query = request.GET.get('q')
    categories = Category.objects.all()
    if query:
        records = VinylRecord.objects.filter(
            Q(title__icontains=query) | Q(artist__icontains=query) | Q(category__name__icontains=query)
        ).distinct().order_by('?')
    else:
        records = VinylRecord.objects.all().order_by('?')
    
    return render(request, 'collection.html', {'records': records, 'categories': categories, 'query': query})

def register(request):
    """Handles User Registration"""
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Log the user in immediately after registering
            return redirect("home")
    else:
        form = RegisterForm()
    
    return render(request, "register.html", {"form": form})
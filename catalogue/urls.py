from django.urls import path
from django.contrib.auth import views as auth_views # Built-in Auth
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('collection/', views.collection, name='collection'),
    path('register/', views.register, name='register'),
    
    # Login and Logout paths
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
]
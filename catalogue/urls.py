from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

# URL map for the catalogue application.
urlpatterns = [
    # --- Public pages ---
    path('', views.home, name='home'),
    path('collection/', views.collection, name='collection'),
    path('artists/', views.artists, name='artists'),
    path('artists/<str:artist_name>/', views.artist_detail, name='artist_detail'),
    path('labels/', views.labels, name='labels'),
    path('labels/<str:label_name>/', views.label_detail, name='label_detail'),
    path('editorial/', views.editorial, name='editorial'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # --- Authentication ---
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # --- Cart / crate ---
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:record_id>/', views.cart_add, name='cart_add'),
    path('cart/update/<int:record_id>/', views.cart_update_quantity, name='cart_update_quantity'),
    path('cart/remove/<int:record_id>/', views.cart_remove, name='cart_remove'),

    # --- Manager dashboard ---
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/add/', views.add_vinyl, name='add_vinyl'),
    path('manager/delete/<int:record_id>/', views.delete_vinyl, name='delete_vinyl'),
    path('manager/stock/<int:record_id>/', views.update_stock, name='update_stock'),

    # --- Membership info page ---
    path('pricing/', views.pricing, name='pricing'),
    path('pricing/update-membership/', views.update_membership, name='update_membership'),
    path('pricing/change-membership/<str:tier>/', views.change_membership, name='change_membership'),
]
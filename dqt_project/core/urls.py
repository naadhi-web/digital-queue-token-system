from django.urls import path
from . import views

urlpatterns = [
    # ========================
    # AUTHENTICATION & PUBLIC
    # ========================
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
    
    # ========================
    # USER DASHBOARD & PROFILE
    # ========================
    path('dashboard/', views.dashboard, name='dashboard'),
    path('my-history/', views.my_history, name='my_history'),
    path('my-reports/', views.my_reports, name='my_reports'),

    # ========================
    # GENERAL TOKEN SYSTEM
    # ========================
    path('book-token/', views.book_token, name='book_token'),
    path('cancel-token/<int:token_id>/', views.cancel_token, name='cancel_token'),
    
    # ========================
    # LIBRARY QUEUE SYSTEM
    # ========================
    path('book-library/', views.book_library, name='book_library'),
    
    # ========================
    # CANTEEN BOOKING SYSTEM
    # ========================
    path('book-canteen/', views.book_canteen, name='book_canteen'),
    
   
    # ========================
    # MANAGEMENT SYSTEM
    # ========================
    path('system/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('system/complete-token/<int:token_id>/', views.complete_token, name='complete_token'),
    path('system/skip-token/<int:token_id>/', views.skip_token, name='skip_token'),
    path('system/reports/', views.reports, name='reports'),
]
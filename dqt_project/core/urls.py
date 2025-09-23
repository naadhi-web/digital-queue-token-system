from django.urls import path
from django.shortcuts import redirect
from . import views

urlpatterns = [ 
    # User authentication and dashboard
    path("", views.home, name="home"),
    path("login/", views.user_login, name="login"),
    path("register/", views.register, name="register"),
    path("dashboard/", views.dashboard, name="dashboard"),

    path("book_token/", views.book_token, name="book_token"),
    path('cancel_token/<int:token_id>/', views.cancel_token, name='cancel_token'),
    path("book/library/", views.book_library, name="book_library"),

    path('canteen/book-canteen/', views.book_canteen_slot, name='book_canteen'),

    # Admin
    path("admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin/complete/<int:token_id>/", views.complete_token, name="complete_token"),
    path("admin/skip/<int:token_id>/", views.skip_token, name="skip_token"),
    path("admin/reports/", views.reports, name="reports"),

    # History
    path("my/history/", views.my_history, name="my_history"),
]

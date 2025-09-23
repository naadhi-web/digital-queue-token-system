from django.contrib import admin
from django.urls import path, include
from core import views as v
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/", admin.site.urls),  # Django admin panel
    path("", include("core.urls")),
    path('canteen/', include('core.urls')), 
    # Optional: only custom logout (login is already in core.urls)
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),

]

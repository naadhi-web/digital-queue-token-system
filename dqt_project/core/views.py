from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import BookingForm
from .forms import UserRegisterForm, BookingForm
from .models import QueueSlot, Token, VisitHistory
from django.shortcuts import render
from .forms import CanteenBookingForm  
from .models import CanteenBooking

def home(request):
    return render(request, "core/home.html")

# -------------------------
# USER AUTH & DASHBOARD
# -------------------------

def user_login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        try:
            username = User.objects.get(email=email).username
            user = authenticate(request, username=username, password=password)
        except User.DoesNotExist:
            user = None

        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid email or password.")
    return render(request, "core/userlogin.html")


def register(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            u = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
            )
            login(request, u)
            messages.success(request, "Registered and logged in.")
            return redirect("dashboard")
    else:
        form = UserRegisterForm()
    return render(request, "core/register.html", {"form": form})


@login_required
def dashboard(request):
    user = request.user
    active_token = Token.objects.filter(is_active=True)
    
    # Assuming "pending" means inactive
    upcoming_slots = Token.objects.filter(is_active=False).exclude(user=user).order_by("issued_at")[:5]
    
    notifications = []  # Replace with Notification.objects.filter(user=user)[:5] if you have a model
    return render(request, "core/dashboard.html", {
        "active_token": active_token,
        "upcoming_slots": upcoming_slots,
        "notifications": notifications
    })


# -------------------------
# TOKEN BOOKING / CANCEL
# -------------------------

@login_required
def book_token(request):
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            slot: QueueSlot = form.cleaned_data["slot"]
            with transaction.atomic():
                used_numbers = set(slot.tokens.select_for_update().values_list("number", flat=True))
                if len(used_numbers) >= slot.max_tokens:
                    messages.error(request, "This slot is full.")
                    return redirect("dashboard")
                for num in range(1, slot.max_tokens + 1):
                    if num not in used_numbers:
                        token = Token.objects.create(slot=slot, user=request.user, number=num)
                        messages.success(request, f"Booked Token #{token.number} for {slot}.")
                        return redirect("dashboard")
    else:
        form = BookingForm()
    return render(request, "core/book_token.html", {"form": form})


@login_required
def cancel_token(request, token_id):
    token = get_object_or_404(Token, id=token_id, user=request.user, status__in=["pending", "approved"])
    token.mark_cancelled()
    VisitHistory.objects.create(
        user=request.user,
        slot=token.slot,
        token_number=token.number,
        outcome="cancelled"
    )
    messages.info(request, "Token cancelled.")
    return redirect("dashboard")
def cancel_token(request, token_id):
    token = get_object_or_404(Token, id=token_id, user=request.user, status__in=["pending", "approved"])
    token.mark_cancelled()
    VisitHistory.objects.create(
        user=request.user,
        slot=token.slot,
        token_number=token.number,
        outcome="cancelled"
    )
    messages.info(request, "Token cancelled.")
    return redirect("dashboard")


# -------------------------
# ADMIN HELPERS
# -------------------------

def is_admin(user):
    return user.is_staff

@user_passes_test(is_admin)
def admin_dashboard(request):
    active_tokens = Token.objects.filter(status="pending").order_by("issued_at")
    return render(request, "core/admin_dashboard.html", {"active_tokens": active_tokens})


@user_passes_test(is_admin)
def complete_token(request, token_id):
    token = get_object_or_404(Token, id=token_id)
    token.mark_served()
    VisitHistory.objects.create(
        user=token.user, slot=token.slot, token_number=token.number, outcome="served"
    )
    messages.success(request, f"Token #{token.number} marked as served.")
    return redirect("admin_dashboard")


@user_passes_test(is_admin)
def skip_token(request, token_id):
    token = get_object_or_404(Token, id=token_id)
    token.mark_skipped()
    VisitHistory.objects.create(
        user=token.user, slot=token.slot, token_number=token.number, outcome="skipped"
    )
    messages.info(request, f"Token #{token.number} skipped.")
    return redirect("admin_dashboard")


@user_passes_test(is_admin)
def reports(request):
    total_today = Token.objects.filter(status="served").count()
    library_count = Token.objects.filter(slot__queue_type="library").count()
    canteen_count = Token.objects.filter(slot__queue_type="canteen").count()
    return render(request, "core/admin_reports.html", {
        "total_today": total_today,
        "library_count": library_count,
        "canteen_count": canteen_count,
    })


@login_required
def my_history(request):
    history = VisitHistory.objects.filter(user=request.user).order_by("-timestamp")
    return render(request, "core/my_history.html", {"history": history})

def book_library(request):
    return book_generic(request, service="library", template="core/book_library.html")

def book_canteen(request):
    return book_generic(request, service="canteen", template="core/book_canteen.html")

def book_generic(request, service, template):
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            slot: QueueSlot = form.cleaned_data["slot"]
            with transaction.atomic():
                used_numbers = set(slot.tokens.select_for_update().values_list("number", flat=True))
                if len(used_numbers) >= slot.max_tokens:
                    messages.error(request, f"This {service} slot is full.")
                    return redirect("dashboard")
                for num in range(1, slot.max_tokens + 1):
                    if num not in used_numbers:
                        token = Token.objects.create(slot=slot, user=request.user, number=num, service=service)
                        messages.success(request, f"Booked {service.capitalize()} Token #{token.number} for {slot}.")
                        return redirect("dashboard")
    else:
        form = BookingForm()
    return render(request, template, {"form": form})

@login_required
def book_canteen_slot(request):
    if request.method == 'POST':
        form = CanteenBookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.save()
            messages.success(request, f"You have successfully booked the slot: {booking.time_slot}")
            return redirect('dashboard')  # Make sure this route exists
    else:
        form = CanteenBookingForm()

    return render(request, 'core/book_slot.html', {'form': form})
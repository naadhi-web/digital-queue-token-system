from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import BookingForm, UserRegisterForm, CanteenTimeSlotBookingForm
from .models import QueueSlot, Token, VisitHistory, CanteenBooking, ActivityLog, Notification

# -------------------------
# HOME
# -------------------------

def home(request):
    return render(request, "core/home.html")

# -------------------------
# USER AUTH
# -------------------------
def user_login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            user = None

        if user is not None:
            login(request, user)
            messages.success(request, "Login successful!")
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid email or password.")
    return render(request, "core/userlogin.html")


def register(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Account created successfully! Welcome, {user.username}!")
            return redirect("dashboard")
        else:
            # Show form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
    else:
        form = UserRegisterForm()
    
    return render(request, "core/register.html", {"form": form})


def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("home")
# -------------------------
# DASHBOARD
# -------------------------

@login_required
def dashboard(request):
    user = request.user
    
    # Get active tokens for the current user
    active_tokens = Token.objects.filter(user=user, status="active").order_by("-issued_at")
    
    # Get upcoming canteen bookings
    upcoming_slots = CanteenBooking.objects.filter(
        user=user, 
        status='confirmed', 
        date__gte=timezone.now().date()
    ).order_by("date", "time_slot")
    
    # Get notifications and activities
    notifications = Notification.objects.filter(user=user, is_read=False).order_by('-created_at')[:5]
    activities = ActivityLog.objects.filter(user=user).order_by('-timestamp')[:10]
    
    return render(request, "core/dashboard.html", {
        "active_tokens": active_tokens,
        "upcoming_slots": upcoming_slots,
        "notifications": notifications,
        "activities": activities,
    })

# -------------------------
# BOOKING TOKEN
# -------------------------

@login_required
def book_token(request):
    if request.method == "POST":
        slot_id = request.POST.get("slot")
        try:
            slot = QueueSlot.objects.get(id=slot_id)
            
            # Check if slot is full
            current_tokens_count = Token.objects.filter(slot=slot, status="active").count()
            if current_tokens_count >= slot.max_tokens:
                messages.error(request, "This slot is full. Please choose another slot.")
                return redirect("book_token")
            
            # Check if user already has active token for this service
            existing_token = Token.objects.filter(
                user=request.user, 
                slot__service=slot.service,
                status="active"
            ).first()
            
            if existing_token:
                messages.error(request, f"You already have an active token for {slot.get_service_display()}.")
                return redirect("dashboard")
            
            # Generate token number
            last_token = Token.objects.filter(slot=slot).order_by('-number').first()
            number = last_token.number + 1 if last_token else 1

            with transaction.atomic():
                token = Token.objects.create(
                    slot=slot,
                    user=request.user,
                    number=number,
                    status="active"
                )
                
                # Log the activity
                ActivityLog.objects.create(
                    user=request.user,
                    action='token_booked',
                    message=f'Token #{token.number} booked for {slot}',
                    object_type='Token'
                )
                
            messages.success(request, f"Token #{token.number} booked successfully for {slot.get_service_display()}!")
            return redirect("dashboard")
            
        except QueueSlot.DoesNotExist:
            messages.error(request, "Invalid slot selected.")
            return redirect("book_token")

    # Get available slots (future slots with capacity)
    slots = QueueSlot.objects.filter(
        date__gte=timezone.now().date()
    ).order_by("date", "start_time")
    
    return render(request, "core/book_token.html", {"slots": slots})

@login_required
def cancel_token(request, token_id):
    token = get_object_or_404(Token, id=token_id, user=request.user, status="active")
    
    with transaction.atomic():
        token.status = "cancelled"
        token.save()
        
        # Create visit history record
        VisitHistory.objects.create(
            user=request.user,
            slot=token.slot,
            token_number=token.number,
            outcome="cancelled"
        )
        
        # Log the activity
        ActivityLog.objects.create(
            user=request.user,
            action='token_cancelled',
            message=f'Token #{token.number} cancelled',
            object_type='Token'
        )
    
    messages.info(request, f"Token #{token.number} cancelled.")
    return redirect("dashboard")

# -------------------------
# BOOKING SERVICES (LIBRARY / CANTEEN)
# -------------------------

@login_required
def book_library(request):
    return book_generic(request, service="library", template="core/book_library.html")

@login_required
def book_canteen(request):
    return book_generic(request, service="canteen", template="core/book_canteen.html")

def book_generic(request, service, template):
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            slot = form.cleaned_data["slot"]
            
            # Check if user already has active token for this service
            existing_token = Token.objects.filter(
                user=request.user, 
                slot__service=service,
                status="active"
            ).first()
            
            if existing_token:
                messages.error(request, f"You already have an active token for {service}.")
                return redirect("dashboard")
            
            with transaction.atomic():
                # Get active tokens count for the slot
                used_numbers = Token.objects.filter(slot=slot, status="active").count()
                
                if used_numbers >= slot.max_tokens:
                    messages.error(request, f"This {service} slot is full.")
                    return redirect("dashboard")

                # Find available number
                last_token = Token.objects.filter(slot=slot).order_by('-number').first()
                number = last_token.number + 1 if last_token else 1
                
                token = Token.objects.create(
                    slot=slot,
                    user=request.user,
                    number=number,
                    status="active"
                )
                
                # Log the activity
                ActivityLog.objects.create(
                    user=request.user,
                    action='token_booked',
                    message=f'{service.capitalize()} Token #{token.number} booked',
                    object_type='Token'
                )
                
            messages.success(request, f"Booked {service.capitalize()} Token #{token.number} for {slot}.")
            return redirect("dashboard")
    else:
        form = BookingForm()
        # Filter slots by service
        form.fields['slot'].queryset = QueueSlot.objects.filter(service=service, date__gte=timezone.now().date())
    
    return render(request, template, {"form": form, "service": service})

# -------------------------
# CANTEEN CUSTOM BOOKING FORM
# -------------------------
@login_required
def book_canteen_slot(request):
    if request.method == "POST":
        form = CanteenTimeSlotBookingForm(request.POST)  # CHANGED THIS LINE
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.status = "confirmed"
            booking.save()
            
            # Log the activity
            ActivityLog.objects.create(
                user=request.user,
                action='booking_made',
                message=f'Canteen booking for {booking.date} @ {booking.time_slot}',
                object_type='CanteenBooking'
            )
            
            messages.success(request, f"You have successfully booked the canteen slot: {booking.time_slot} on {booking.date}")
            return redirect("dashboard")
    else:
        form = CanteenTimeSlotBookingForm()  # CHANGED THIS LINE

    return render(request, "core/book_canteen.html", {"form": form})

# -------------------------
# USER HISTORY
# -------------------------
@login_required
def my_history(request):
    tokens_history = Token.objects.filter(user=request.user).order_by("-issued_at")
    visit_history = VisitHistory.objects.filter(user=request.user).order_by("-timestamp")
    
    # Get only the fields that definitely exist
    bookings_history = CanteenBooking.objects.filter(user=request.user).values(
        'id', 'date', 'time_slot', 'purpose'
    ).order_by("-id")
    
    return render(request, "core/my_history.html", {
        "tokens_history": tokens_history,
        "visit_history": visit_history,
        "bookings_history": bookings_history,
    })

# -------------------------
# ADMIN HELPERS
# -------------------------

def is_admin(user):
    return user.is_staff

@user_passes_test(is_admin)
def admin_dashboard(request):
    active_tokens = Token.objects.filter(status="active").order_by("issued_at")
    today_bookings = CanteenBooking.objects.filter(date=timezone.now().date())
    
    return render(request, "core/admin_dashboard.html", {
        "active_tokens": active_tokens,
        "today_bookings": today_bookings,
    })

@user_passes_test(is_admin)
def complete_token(request, token_id):
    token = get_object_or_404(Token, id=token_id)
    
    with transaction.atomic():
        token.mark_served()
        
        VisitHistory.objects.create(
            user=token.user,
            slot=token.slot,
            token_number=token.number,
            outcome="completed"
        )
        
        # Create notification for user
        Notification.objects.create(
            user=token.user,
            title="Token Completed",
            message=f"Your token #{token.number} has been completed.",
            notification_type='token_ready'
        )
    
    messages.success(request, f"Token #{token.number} marked as completed.")
    return redirect("admin_dashboard")

@user_passes_test(is_admin)
def skip_token(request, token_id):
    token = get_object_or_404(Token, id=token_id)
    
    with transaction.atomic():
        token.mark_skipped()
        
        VisitHistory.objects.create(
            user=token.user,
            slot=token.slot,
            token_number=token.number,
            outcome="skipped"
        )
    
    messages.info(request, f"Token #{token.number} skipped.")
    return redirect("admin_dashboard")

@user_passes_test(is_admin)
def reports(request):
    today = timezone.now().date()
    
    total_today = Token.objects.filter(
        status="completed",
        issued_at__date=today
    ).count()
    
    library_count = Token.objects.filter(slot__service="library", issued_at__date=today).count()
    canteen_count = Token.objects.filter(slot__service="canteen", issued_at__date=today).count()
    active_tokens = Token.objects.filter(status="active").count()
    
    return render(request, "core/admin_reports.html", {
        "total_today": total_today,
        "library_count": library_count,
        "canteen_count": canteen_count,
        "active_tokens": active_tokens,
        "today": today,
    })
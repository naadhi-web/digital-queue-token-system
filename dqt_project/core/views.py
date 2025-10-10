from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Count, Q  
from django.utils import timezone
from datetime import timedelta
import logging

from .forms import BookingForm, UserRegisterForm
from .models import QueueSlot, Token, VisitHistory, CanteenBooking, ActivityLog, Notification
from . import models
from django.db import models
from django.db import DatabaseError
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

logger = logging.getLogger(__name__)
@login_required
def dashboard(request):
    user = request.user
    today = timezone.now().date()
    
    try:
        # Get active tokens for the current user
        active_tokens = Token.objects.filter(user=user, status="active").order_by("-issued_at")
        
        # Get upcoming canteen bookings
        upcoming_slots = CanteenBooking.objects.filter(
            user=user, 
            date__gte=today
        ).order_by("date", "time_slot")
        
        # Get notifications and activities
        activities = ActivityLog.objects.filter(user=user).order_by('-timestamp')[:10]
        notifications = Notification.objects.filter(user=user).order_by('-created_at')[:5]
        
        # Add reports data for staff users
        today_stats = {}
        recent_reports = []
        
        if user.is_staff:
            # Today's statistics
            today_stats = {
                'total_tokens': Token.objects.filter(issued_at__date=today).count(),
                'served_tokens': Token.objects.filter(status='completed', issued_at__date=today).count(),
                'active_tokens': Token.objects.filter(status='active').count(),
                'total_bookings': CanteenBooking.objects.filter(date=today).count(),
            }
            
            # Recent reports data (last 7 days)
            last_week = today - timedelta(days=7)
            
            # Fixed: Use Count and Q from django.db.models
            recent_reports = Token.objects.filter(
                issued_at__date__gte=last_week
            ).extra({
                'date': "date(issued_at)"
            }).values('date', 'slot__service').annotate(
                total=Count('id'),
                served=Count('id', filter=Q(status='completed')),
                skipped=Count('id', filter=Q(status='skipped')),
                cancelled=Count('id', filter=Q(status='cancelled'))
            ).order_by('-date')[:5]
        
        return render(request, "core/dashboard.html", {
            "active_tokens": active_tokens,
            "upcoming_slots": upcoming_slots,
            "notifications": notifications,
            "activities": activities,
            "today_stats": today_stats,
            "recent_reports": recent_reports,
        })
        
    except DatabaseError as e:
        logger.error(f"Database error in dashboard: {e}")
        # Return a simplified version or error page
        return render(request, "core/dashboard.html", {
            "active_tokens": [],
            "upcoming_slots": [],
            "notifications": [],
            "activities": [],
            "today_stats": {},
            "recent_reports": [],
            "error": "Unable to load dashboard data"
        })
    except Exception as e:
        logger.error(f"Unexpected error in dashboard: {e}")
        # Return a simplified version for any other errors
        return render(request, "core/dashboard.html", {
            "active_tokens": [],
            "upcoming_slots": [],
            "notifications": [],
            "activities": [],
            "today_stats": {},
            "recent_reports": [],
            "error": "An unexpected error occurred"
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

@login_required
def admin_dashboard(request):
    """Admin dashboard with real-time statistics"""
    if not request.user.is_staff:
        return redirect('dashboard')
    
    today = timezone.now().date()
    print(f"🔍 DEBUG: Today's date is {today}")
    
    # Check ALL tokens first
    all_tokens = Token.objects.all()
    print(f"🔍 DEBUG: Total tokens in database: {all_tokens.count()}")
    
    # Check token dates and statuses
    for token in all_tokens[:5]:  # First 5 tokens
        print(f"🔍 DEBUG: Token #{token.id} - Date: {token.issued_at.date() if token.issued_at else 'No date'} - Status: {token.status}")
    
    # Today's statistics - try different date filters
    today_tokens = Token.objects.filter(issued_at__date=today)
    print(f"🔍 DEBUG: Today tokens (date filter): {today_tokens.count()}")
    
    # Alternative date filter
    today_tokens_alt = Token.objects.filter(
        issued_at__year=today.year,
        issued_at__month=today.month, 
        issued_at__day=today.day
    )
    print(f"🔍 DEBUG: Today tokens (alternative filter): {today_tokens_alt.count()}")
    
    # Use the alternative filter if it works better
    today_tokens = today_tokens_alt
    
    total_tokens_today = today_tokens.count()
    served_today = today_tokens.filter(status='completed').count()
    
    print(f"🔍 DEBUG: Total tokens today: {total_tokens_today}")
    print(f"🔍 DEBUG: Served today: {served_today}")
    
    # Service-wise breakdown for today
    library_today = today_tokens.filter(slot__service='library').count()
    canteen_today = today_tokens.filter(slot__service='canteen').count()
    
    print(f"🔍 DEBUG: Library today: {library_today}")
    print(f"🔍 DEBUG: Canteen today: {canteen_today}")
    
    # Check all statuses
    all_pending = Token.objects.filter(status='pending')
    all_active = Token.objects.filter(status='active')
    all_completed = Token.objects.filter(status='completed')
    
    print(f"🔍 DEBUG: All pending tokens: {all_pending.count()}")
    print(f"🔍 DEBUG: All active tokens: {all_active.count()}")
    print(f"🔍 DEBUG: All completed tokens: {all_completed.count()}")
    
    # Pending tokens (all time for now)
    pending_tokens = all_pending
    active_tokens = all_active
    
    print(f"🔍 DEBUG: Pending tokens: {pending_tokens.count()}")
    print(f"🔍 DEBUG: Active tokens: {active_tokens.count()}")
    
    # ALL active tokens for the comprehensive table (including pending and active)
    all_active_tokens = Token.objects.filter(status__in=['pending', 'active']).order_by('issued_at')
    print(f"🔍 DEBUG: All active tokens for table: {all_active_tokens.count()}")
    
    context = {
        'total_tokens_today': total_tokens_today,
        'served_today': served_today,
        'library_today': library_today,
        'canteen_today': canteen_today,
        'pending_tokens': pending_tokens,
        'active_tokens': active_tokens,
        'all_active_tokens': all_active_tokens,  # This is for the table
        'today': today,
    }
    
    return render(request, 'core/admin_dashboard.html', context)


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
    
    return render(request, "core/reports.html", {
        "total_today": total_today,
        "library_count": library_count,
        "canteen_count": canteen_count,
        "active_tokens": active_tokens,
        "today": today,
    })

def staff_required(view_func):
    """Decorator to ensure user is staff"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            from django.shortcuts import redirect
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
def reports(request):
    """Reports page for both users and staff"""
    if request.user.is_staff:
        # Show admin reports with system-wide data
        return admin_reports(request)
    else:
        # Show user-specific reports - redirect to my_reports
        return my_reports(request)

def admin_reports(request):
    """Staff-only system reports"""
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    
    # Generate report data - manual date extraction
    reports_data = Token.objects.filter(
        issued_at__date__gte=last_30_days
    ).extra({
        'date': "date(issued_at)"
    }).values('date', 'slot__service').annotate(
        total=Count('id'),
        served=Count('id', filter=Q(status='completed')),
        skipped=Count('id', filter=Q(status='skipped')),
        cancelled=Count('id', filter=Q(status='cancelled'))
    ).order_by('-date', 'slot__service')
    
    # Debug: print the data to see what's coming through
    print("Reports data:", list(reports_data))
    
    # Format data for template
    reports = []
    for stat in reports_data:
        # Ensure date is properly formatted
        date_obj = stat['date']
        if isinstance(date_obj, str):
            # If it's a string, convert to date object
            from datetime import datetime
            date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
        
        reports.append({
            'date': date_obj,
            'queue_type': stat['slot__service'] or 'general',
            'total': stat['total'],
            'served': stat['served'],
            'skipped': stat['skipped'],
            'cancelled': stat['cancelled'],
        })
    
    # Calculate totals for summary cards
    total_tokens = sum(report['total'] for report in reports)
    total_served = sum(report['served'] for report in reports)
    total_skipped = sum(report['skipped'] for report in reports)
    total_cancelled = sum(report['cancelled'] for report in reports)
    
    context = {
        'reports': reports,
        'is_staff': True,
        'total_tokens': total_tokens,
        'total_served': total_served,
        'total_skipped': total_skipped,
        'total_cancelled': total_cancelled,
    }
    
    return render(request, 'core/reports.html', context)


@login_required
def my_reports(request):
    """User-specific reports page"""
    user = request.user
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    
    # Token statistics
    user_tokens = Token.objects.filter(user=user)
    recent_tokens = user_tokens.filter(issued_at__date__gte=last_30_days)
    
    token_stats = {
        'total_tokens': user_tokens.count(),
        'completed_tokens': user_tokens.filter(status='completed').count(),
        'active_tokens': user_tokens.filter(status='active').count(),
        'cancelled_tokens': user_tokens.filter(status='cancelled').count(),
    }
    
    # Canteen statistics
    canteen_stats = {
        'total_bookings': CanteenBooking.objects.filter(user=user).count(),
        'recent_bookings': CanteenBooking.objects.filter(user=user, date__gte=last_30_days).count(),
    }
    
    # Service usage statistics
    service_stats_data = recent_tokens.values('slot__service').annotate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='completed'))
    ).order_by('-total')
    
    service_stats = []
    for stat in service_stats_data:
        service_stats.append({
            'service': stat['slot__service'] or 'General',
            'total': stat['total'],
            'completed': stat['completed'],
        })
    
    # Recent tokens for activity feed
    recent_tokens_list = recent_tokens.order_by('-issued_at')[:10]
    
    # Monthly breakdown
    monthly_stats_data = user_tokens.extra({
        'month': "strftime('%%Y-%%m', issued_at)"
    }).values('month').annotate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='completed')),
        cancelled=Count('id', filter=Q(status='cancelled'))
    ).order_by('-month')[:6]  # Last 6 months
    
    monthly_stats = []
    for stat in monthly_stats_data:
        monthly_stats.append({
            'month': stat['month'],
            'total': stat['total'],
            'completed': stat['completed'],
            'cancelled': stat['cancelled'],
        })
    
    context = {
        "is_staff": False,
        "token_stats": token_stats,
        "canteen_stats": canteen_stats,
        "service_stats": service_stats,
        "recent_tokens": recent_tokens_list,
        "monthly_stats": monthly_stats,
    }
    
    return render(request, "core/my_reports.html", context)
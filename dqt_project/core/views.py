from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import UserRegisterForm, BookingForm, QueueSlotForm, RescheduleForm
from .models import QueueSlot, Token, VisitHistory

def staff_required(view):
    return user_passes_test(lambda u: u.is_authenticated and u.is_staff)(view)

def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
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
        form = RegisterForm()
    return render(request, "core/register.html", {"form": form})

@login_required
def dashboard(request):
    today = timezone.localdate()
    active_tokens = Token.objects.filter(user=request.user, status__in=["pending","approved"]).select_related("slot")
    upcoming_slots = QueueSlot.objects.filter(date__gte=today).order_by("date","start_time")[:10]
    return render(request, "core/dashboard.html", {
        "active_tokens": active_tokens,
        "upcoming_slots": upcoming_slots
    })

@login_required
def book_token(request):
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            slot: QueueSlot = form.cleaned_data["slot"]
            used_numbers = set(slot.tokens.values_list("number", flat=True))
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
    return render(request, "core/book.html", {"form": form})

@login_required
def cancel_token(request, token_id):
    token = get_object_or_404(Token, id=token_id, user=request.user, status__in=["pending","approved"])
    token.mark_cancelled()
    VisitHistory.objects.create(user=request.user, slot=token.slot, token_number=token.number, outcome="cancelled")
    messages.info(request, "Token cancelled.")
    return redirect("dashboard")

@staff_required
def list_slots(request):
    slots = QueueSlot.objects.order_by("-date","start_time")
    return render(request, "core/slots.html", {"slots": slots})

@staff_required
def create_slot(request):
    if request.method == "POST":
        form = QueueSlotForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Slot created.")
            return redirect("list_slots")
    else:
        form = QueueSlotForm()
    return render(request, "core/slot_form.html", {"form": form, "title": "New Slot"})

@staff_required
def edit_slot(request, slot_id):
    slot = get_object_or_404(QueueSlot, id=slot_id)
    if request.method == "POST":
        form = QueueSlotForm(request.POST, instance=slot)
        if form.is_valid():
            form.save()
            messages.success(request, "Slot updated.")
            return redirect("list_slots")
    else:
        form = QueueSlotForm(instance=slot)
    return render(request, "core/slot_form.html", {"form": form, "title": "Edit Slot"})

@staff_required
def monitor_queue(request, slot_id):
    slot = get_object_or_404(QueueSlot, id=slot_id)
    tokens = slot.tokens.select_related("user").all()
    pending = [t for t in tokens if t.status in ("pending","approved")]
    for idx, t in enumerate(pending):
        t.eta_minutes = slot.estimate_wait_minutes(idx)
    return render(request, "core/monitor.html", {"slot": slot, "tokens": tokens})

@staff_required
def approve_token(request, token_id):
    token = get_object_or_404(Token, id=token_id, status__in=["pending","approved"])
    token.mark_approved()
    messages.success(request, f"Token #{token.number} approved.")
    return redirect("monitor_queue", slot_id=token.slot.id)

@staff_required
def skip_token(request, token_id):
    token = get_object_or_404(Token, id=token_id, status__in=["pending","approved"])
    token.mark_skipped()
    VisitHistory.objects.create(user=token.user, slot=token.slot, token_number=token.number, outcome="skipped")
    messages.success(request, f"Token #{token.number} skipped.")
    return redirect("monitor_queue", slot_id=token.slot.id)

@staff_required
def serve_token(request, token_id):
    token = get_object_or_404(Token, id=token_id, status__in=["approved","pending"])
    token.mark_served()
    VisitHistory.objects.create(user=token.user, slot=token.slot, token_number=token.number, outcome="served")
    messages.success(request, f"Token #{token.number} marked served.")
    return redirect("monitor_queue", slot_id=token.slot.id)

@login_required
def my_history(request):
    history = VisitHistory.objects.filter(user=request.user).order_by("-timestamp")
    return render(request, "core/my_history.html", {"history": history})

@staff_required
def reschedule_token(request, token_id):
    token = get_object_or_404(Token, id=token_id, status__in=["pending","approved"])
    if request.method == "POST":
        form = RescheduleForm(request.POST)
        if form.is_valid():
            new_slot = form.cleaned_data["new_slot"]
            used_numbers = set(new_slot.tokens.values_list("number", flat=True))
            if len(used_numbers) >= new_slot.max_tokens:
                messages.error(request, "New slot is full.")
                return redirect("monitor_queue", slot_id=token.slot.id)
            for num in range(1, new_slot.max_tokens + 1):
                if num not in used_numbers:
                    token.slot = new_slot
                    token.number = num
                    token.save()
                    messages.success(request, f"Token moved to {new_slot}.")
                    return redirect("monitor_queue", slot_id=new_slot.id)
    else:
        form = RescheduleForm()
    return render(request, "core/reschedule.html", {"form": form, "token": token})

@staff_required
def reports_summary(request):
    # simple summary counts; extend for charts
    total_slots = QueueSlot.objects.count()
    total_tokens = Token.objects.count()
    served = Token.objects.filter(status="served").count()
    pending = Token.objects.filter(status__in=["pending","approved"]).count()
    context = {
        "total_slots": total_slots,
        "total_tokens": total_tokens,
        "served": served,
        "pending": pending
    }
    return render(request, "core/reports.html", context)

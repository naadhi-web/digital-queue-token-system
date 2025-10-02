from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone

class QueueSlot(models.Model):
    SERVICE_CHOICES = [
        ('library', 'Library'),
        ('canteen', 'Canteen'),
    ]
    service = models.CharField(max_length=50, choices=SERVICE_CHOICES)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_tokens = models.IntegerField(default=10)

    def __str__(self):
        return f"{self.get_service_display()} - {self.date} {self.start_time}-{self.end_time}"

    @property
    def queue_type(self):
        return self.service

class Slot(models.Model):
    name = models.CharField(max_length=100)
    time = models.DateTimeField()

    def __str__(self):
        return self.name
    
class Token(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("skipped", "Skipped"),
    ]
    
    slot = models.ForeignKey(QueueSlot, related_name="tokens", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    issued_at = models.DateTimeField(auto_now_add=True)
    service = models.CharField(max_length=50, choices=QueueSlot.SERVICE_CHOICES, blank=True, null=True)

    class Meta:
        ordering = ['-issued_at']

    def __str__(self):
        return f"Token #{self.number} ({self.slot})"

    def save(self, *args, **kwargs):
        if not self.service and self.slot:
            self.service = self.slot.service
        super().save(*args, **kwargs)

    def mark_served(self):
        self.status = "completed"
        self.save()

    def mark_skipped(self):
        self.status = "skipped"
        self.save()

class VisitHistory(models.Model):
    OUTCOME_CHOICES = [
        ("completed", "Completed"),
        ("skipped", "Skipped"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    slot = models.ForeignKey(QueueSlot, on_delete=models.SET_NULL, null=True, blank=True)
    token_number = models.PositiveIntegerField()
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Visit Histories"

    def __str__(self):
        if self.slot:
            return f"{self.user.username} - {self.slot} - T{self.token_number} - {self.outcome}"
        return f"{self.user.username} - T{self.token_number} - {self.outcome}"
    
class CanteenBooking(models.Model):
    TIME_SLOT_CHOICES = [
        ('8:00-9:00', '8:00-9:00 AM'),
        ('9:00-10:00', '9:00-10:00 AM'),
        ('12:00-1:00', '12:00-1:00 PM'),
        ('1:00-2:00', '1:00-2:00 PM'),
    ]
    
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    time_slot = models.CharField(max_length=50, choices=TIME_SLOT_CHOICES)
    purpose = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    booked_at = models.DateTimeField(auto_now_add=True)  # This field was missing

    class Meta:
        ordering = ['-booked_at']

    def __str__(self):
        return f"{self.user.username} - {self.date} @ {self.time_slot}"
    
    
class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('token_booked', 'Token Booked'),
        ('token_cancelled', 'Token Cancelled'),
        ('token_completed', 'Token Completed'),
        ('booking_made', 'Booking Made'),
        ('login', 'User Login'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    message = models.TextField()
    object_type = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

class Notification(models.Model):
    TYPE_CHOICES = [
        ('token_ready', 'Your Token is Ready'),
        ('booking_confirmed', 'Booking Confirmed'),
        ('system', 'System Notification'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='system')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"
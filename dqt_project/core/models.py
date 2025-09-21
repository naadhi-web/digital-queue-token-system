from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone # type: ignore

class QueueSlot(models.Model):
    SERVICE_CHOICES = [
        ('library', 'Library'),
        ('canteen', 'Canteen'),
    ]
    service = models.CharField(max_length=50, choices=SERVICE_CHOICES)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_tokens = models.IntegerField()

    def __str__(self):
        return f"{self.get_service_display()} - {self.date} {self.start_time}-{self.end_time}"
    
class Slot(models.Model):
    name = models.CharField(max_length=100)
    time = models.DateTimeField()

    def __str__(self):
        return self.name
    
class Token(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("skipped", "Skipped"),
        ("served", "Served"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    ]
    number = models.PositiveIntegerField()
    service = models.CharField(max_length=100)  # type of service (Library/Canteen)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    is_active = models.BooleanField(default=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    slot = models.ForeignKey(QueueSlot, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Token {self.id} - {self.user.username} ({self.slot})"



class VisitHistory(models.Model):
    OUTCOME_CHOICES = [
        ("served", "Served"),
        ("skipped", "Skipped"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    slot = models.ForeignKey(QueueSlot, on_delete=models.SET_NULL, null=True)
    token_number = models.PositiveIntegerField()
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.slot} - T{self.token_number} - {self.outcome}"
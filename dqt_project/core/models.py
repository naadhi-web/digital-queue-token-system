from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
class QueueSlot(models.Model):
    QUEUE_TYPE_CHOICES = [
        ("library", "Library"),
        ("canteen", "Canteen"),
    ]
    name = models.CharField(max_length=100)
    queue_type = models.CharField(max_length=20, choices=QUEUE_TYPE_CHOICES)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_tokens = models.PositiveIntegerField(default=100)
    avg_service_minutes = models.PositiveIntegerField(default=2)

    def __str__(self):
        return f"{self.name} ({self.queue_type}) - {self.date}"

    @property
    def active_count(self):
        return self.tokens.filter(status__in=["pending","approved"]).count()

    def estimate_wait_minutes(self, position_index: int) -> int:
        return position_index * self.avg_service_minutes

class Token(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("skipped", "Skipped"),
        ("served", "Served"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    slot = models.ForeignKey("QueueSlot", on_delete=models.CASCADE, related_name="tokens")
    number = models.PositiveIntegerField()  # each token in a slot gets a unique number
    issued_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    class Meta:
        unique_together = ("slot", "number")
        ordering = ["number"]

    def __str__(self):
        return f"{self.slot} - T{self.number} ({self.user.username})"

    def mark_approved(self):
        self.status = "approved"
        self.approved_at = timezone.now()
        self.save()

    def mark_served(self):
        self.status = "served"
        self.served_at = timezone.now()
        self.save()

    def mark_skipped(self):
        self.status = "skipped"
        self.save()

    def mark_cancelled(self):
        self.status = "cancelled"
        self.cancelled_at = timezone.now()
        self.save()


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












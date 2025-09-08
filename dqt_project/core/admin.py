from django.contrib import admin
from .models import QueueSlot, Token, VisitHistory

@admin.register(QueueSlot)
class QueueSlotAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "queue_type", "date", "start_time", "end_time", "max_tokens")
    list_filter = ("queue_type", "date")
    search_fields = ("name",)

@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    # Use only fields that really exist in your Token model
    list_display = ("id", "slot", "user", "number", "status")
    list_filter = ("status", "slot__queue_type", "slot__date")
    search_fields = ("user__username", "slot__name")

@admin.register(VisitHistory)
class VisitHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "slot", "token_number", "outcome", "timestamp")
    list_filter = ("outcome", "timestamp")
    search_fields = ("user__username", "slot__name")

from django.contrib import admin
from .models import QueueSlot, Token, VisitHistory

admin.site.site_header = "My Custom Admin"
admin.site.site_title = "My Custom Admin Portal"
admin.site.index_title = "Welcome to the Admin Panel"

@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'slot', 'issued_at', 'is_active')
    list_filter = ('is_active', 'slot__service')  # ✅ updated from slot__queue_type → slot__service


@admin.register(VisitHistory)
class VisitHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "slot", "token_number", "outcome", "timestamp")
    list_filter = ("outcome", "timestamp")
    search_fields = ("user__username", "slot__name")

@admin.register(QueueSlot)
class QueueSlotAdmin(admin.ModelAdmin):
    list_display = ('id', 'service', 'date', 'start_time', 'end_time', 'max_tokens')
    list_filter = ('service', 'date')  # use 'service' instead of queue_type

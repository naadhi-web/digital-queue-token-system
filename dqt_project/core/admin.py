from django.contrib import admin
from .models import QueueSlot, Token, VisitHistory, CanteenBooking, ActivityLog, Notification
from django.urls import path
from django.shortcuts import render
from django.db.models import Count, Avg
import datetime

# Customize Admin Headers
admin.site.site_header = "Digital Queue Token System Admin"
admin.site.site_title = "Queue System Admin Portal"
admin.site.index_title = "Welcome to Queue System Admin Panel"

@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('number', 'user', 'slot_service', 'service', 'status', 'issued_at')
    list_filter = ('status', 'service', 'issued_at')
    search_fields = ('user__username', 'number', 'slot__service')
    readonly_fields = ('issued_at',)

    def slot_service(self, obj):
        return obj.slot.service if obj.slot else '-'
    slot_service.short_description = 'Slot Service'

class ReportsAdmin(admin.ModelAdmin):
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('reports/', self.admin_site.admin_view(self.reports_view), name='core_reports'),
        ]
        return custom_urls + urls

    def reports_view(self, request):
        # Generate report data
        today = datetime.date.today()
        
        # Example report data
        total_tokens = Token.objects.count()
        today_tokens = Token.objects.filter(issued_at__date=today).count()
        completed_visits = VisitHistory.objects.filter(outcome='completed').count()
        
        context = {
            'total_tokens': total_tokens,
            'today_tokens': today_tokens,
            'completed_visits': completed_visits,
            'title': 'System Reports'
        }
        return render(request, 'admin/core/reports.html', context)

@admin.register(QueueSlot)
class QueueSlotAdmin(admin.ModelAdmin):
    list_display = ('id', 'service', 'date', 'start_time', 'end_time', 'max_tokens', 'tokens_count')
    list_filter = ('service', 'date')
    search_fields = ('service',)
    date_hierarchy = 'date'

    def tokens_count(self, obj):
        return obj.tokens.count()
    tokens_count.short_description = 'Tokens Booked'

@admin.register(VisitHistory)
class VisitHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "slot_info", "token_number", "outcome", "timestamp")
    list_filter = ("outcome", "timestamp")
    search_fields = ("user__username", "slot__service")
    readonly_fields = ('timestamp',)

    def slot_info(self, obj):
        return str(obj.slot) if obj.slot else 'No Slot'
    slot_info.short_description = 'Slot'

@admin.register(CanteenBooking)
class CanteenBookingAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "date", "time_slot", "status", "purpose_preview")
    list_filter = ("status", "date", "time_slot")
    search_fields = ("user__username", "purpose")
    
    def purpose_preview(self, obj):
        return obj.purpose[:50] + "..." if len(obj.purpose) > 50 else obj.purpose
    purpose_preview.short_description = 'Purpose'

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "action", "object_type", "timestamp", "message_preview")
    list_filter = ("action", "object_type", "timestamp")
    search_fields = ("user__username", "message")
    readonly_fields = ('timestamp',)

    def message_preview(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("user__username", "title", "message")
    readonly_fields = ('created_at',)
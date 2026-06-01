from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "kind", "recipient", "bot", "is_sent", "is_read", "created_at")
    list_filter = ("kind", "bot", "is_sent", "is_read")
    search_fields = ("recipient__username", "title", "body")
    readonly_fields = ("created_at", "sent_at")
    autocomplete_fields = ("recipient",)

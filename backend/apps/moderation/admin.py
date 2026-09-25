from django.contrib import admin

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "reporter", "reported_user", "reason", "created_at")
    list_filter = ("reason",)
    search_fields = ("reporter__username", "reported_user__username", "comment")
    readonly_fields = ("created_at",)

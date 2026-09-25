from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "vet", "client", "stars", "created_at")
    list_filter = ("stars",)
    search_fields = ("vet__user__username", "client__username", "comment")
    readonly_fields = ("created_at",)

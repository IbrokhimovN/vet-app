from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AuthIdentity, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "telegram_id", "role", "phone", "is_active")
    list_filter = ("role", "language", "is_active", "is_staff")
    search_fields = ("username", "telegram_id", "phone", "first_name", "last_name")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Vet-App", {"fields": ("telegram_id", "role", "phone", "language", "photo_url")}),
    )


@admin.register(AuthIdentity)
class AuthIdentityAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "external_id", "is_verified", "created_at")
    list_filter = ("provider", "is_verified")
    search_fields = ("external_id", "user__username")

from django.contrib import admin

from .models import CallRequest, Offer, ServiceRequest


@admin.register(CallRequest)
class CallRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "vet", "type", "status", "created_at")
    list_filter = ("type", "status")
    search_fields = ("client__username", "vet__user__username")


class OfferInline(admin.TabularInline):
    model = Offer
    extra = 0


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "specialization", "type", "status", "created_at")
    list_filter = ("type", "status")
    search_fields = ("client__username",)
    inlines = [OfferInline]


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("id", "request", "vet", "price", "status", "created_at")
    list_filter = ("status",)

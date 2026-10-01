from django.contrib import admin

from .models import Clinic, Service, Specialization, VetProfile


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(VetProfile)
class VetProfileAdmin(admin.ModelAdmin):
    list_display = (
        "__str__", "city", "is_verified", "is_available", "is_top",
        "rating_avg", "rating_count",
    )
    list_filter = ("is_verified", "is_available", "is_top", "specializations")
    search_fields = ("user__username", "user__first_name", "clinic_name", "city")
    filter_horizontal = ("specializations",)
    inlines = [ServiceInline]
    # rating/monetizatsiya maydonlari tizim tomonidan boshqariladi
    readonly_fields = ("rating_avg", "rating_count", "created_at", "updated_at")


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "phone", "is_verified", "is_active")
    list_filter = ("is_verified", "is_active", "city")
    search_fields = ("name", "address", "phone")

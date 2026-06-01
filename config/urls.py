"""Asosiy URL marshrutlari. Barcha API /api/v1/ ostida (ARCHITECTURE.md 14-bo'lim)."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

api_v1 = [
    path("auth/", include("apps.accounts.urls")),
    path("", include("apps.vets.urls")),
    path("", include("apps.pets.urls")),
    path("", include("apps.requests.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.reviews.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include((api_v1, "api"), namespace="v1")),
]

# --- Mini App frontlari (ARCHITECTURE.md 14: headless API + alohida front) ---
# Dev'da Django serve qiladi; prod'da Nginx static sifatida beradi.
FRONTEND = settings.BASE_DIR / "frontend"
urlpatterns += [
    path("vet/", serve, {"path": "index.html", "document_root": FRONTEND / "vet"}),
    re_path(r"^vet/(?P<path>.+)$", serve, {"document_root": FRONTEND / "vet"}),
    path("client/", serve, {"path": "index.html", "document_root": FRONTEND / "client"}),
    re_path(r"^client/(?P<path>.+)$", serve, {"document_root": FRONTEND / "client"}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

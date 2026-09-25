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
    path("", include("apps.moderation.urls")),
    path("admin/", include("apps.adminpanel.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include((api_v1, "api"), namespace="v1")),
]

# --- Mini App frontlari (dev qulayligi) ---
# Frontend alohida papka (../frontend). Dev'da (frontend papkasi yonida turganda)
# Django shu yerdan ham beradi. Docker/prod'da frontend alohida konteyner (Caddy)
# va bu qism o'z-o'zidan o'chadi, chunki backend konteynerida frontend papkasi yo'q.
FRONTEND = settings.FRONTEND_DIR


def serve_no_cache(request, *args, **kwargs):
    # Telegram WebView Cache-Control bo'lmasa eski app.js/style.css'ni keshda ushlab qoladi.
    response = serve(request, *args, **kwargs)
    response["Cache-Control"] = "no-cache"
    return response


if FRONTEND.is_dir():
    for _name, _dir in (("vet", "vet"), ("admin-panel", "admin"), ("client", "client"), ("legal", "legal")):
        urlpatterns += [
            path(f"{_name}/", serve_no_cache, {"path": "index.html", "document_root": FRONTEND / _dir}),
            re_path(rf"^{_name}/(?P<path>.+)$", serve_no_cache, {"document_root": FRONTEND / _dir}),
        ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

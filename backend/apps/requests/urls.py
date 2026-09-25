"""requests API marshrutlari (ARCHITECTURE.md 6.2–6.3)."""
from django.urls import path

from .views import (
    CallRequestActionView,
    CallRequestListCreateView,
    CallRequestSetPriceView,
    OfferAcceptView,
    OfferCreateView,
    OfferWithdrawView,
    ServiceRequestCancelView,
    ServiceRequestCompleteView,
    ServiceRequestFeedView,
    ServiceRequestListCreateView,
    ServiceRequestOffersView,
    ServiceRequestWonView,
)

urlpatterns = [
    # REJIM A — to'g'ridan chaqiruv
    path("requests/", CallRequestListCreateView.as_view(), name="call-list"),
    path("requests/<int:pk>/price/", CallRequestSetPriceView.as_view(), name="call-set-price"),
    path("requests/<int:pk>/<str:action>/", CallRequestActionView.as_view(), name="call-action"),

    # REJIM B — tender (ochiq so'rov + takliflar)
    path("service-requests/", ServiceRequestListCreateView.as_view(), name="sr-list"),
    path("service-requests/feed/", ServiceRequestFeedView.as_view(), name="sr-feed"),
    path("service-requests/won/", ServiceRequestWonView.as_view(), name="sr-won"),
    path("service-requests/<int:pk>/offers/", ServiceRequestOffersView.as_view(), name="sr-offers"),
    path("service-requests/<int:pk>/offer/", OfferCreateView.as_view(), name="sr-offer-create"),
    path("service-requests/<int:pk>/cancel/", ServiceRequestCancelView.as_view(), name="sr-cancel"),
    path("service-requests/<int:pk>/complete/", ServiceRequestCompleteView.as_view(), name="sr-complete"),
    path("offers/<int:pk>/accept/", OfferAcceptView.as_view(), name="offer-accept"),
    path("offers/<int:pk>/withdraw/", OfferWithdrawView.as_view(), name="offer-withdraw"),
]

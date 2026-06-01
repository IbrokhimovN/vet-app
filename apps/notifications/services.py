"""
Bildirishnoma servis qatlami (ARCHITECTURE.md 7-bo'lim).

View'lar shu yerdagi funksiyalarni chaqiradi. Har biri Notification yozuvini
yaratadi va yetkazishni Celery'ga topshiradi. Bot qabul qiluvchi rolidan kelib
chiqadi (vet -> vet bot, mijoz -> client bot).
"""
from .models import Notification, NotificationKind
from .tasks import deliver_notification, fanout_tender

TYPE_LABEL = {"home": "🏠 Uyga chaqirish", "online": "💬 Online", "contact": "📞 Kontakt"}


def _push(recipient, kind, title, body, **links):
    """Notification yaratadi va Telegram'ga yetkazishni navbatga qo'yadi."""
    if recipient is None or not getattr(recipient, "is_active", True):
        return None
    bot = "vet" if recipient.is_vet else "client"
    n = Notification.objects.create(
        recipient=recipient, kind=kind, title=title, body=body, bot=bot, **links
    )
    deliver_notification.delay(n.pk)
    return n


# --------------------------- REJIM A: CallRequest ---------------------------

def notify_new_call(call):
    """Vetga yangi chaqiruv kelganini bildiradi."""
    label = TYPE_LABEL.get(call.type, call.type)
    pet = call.pet.name if call.pet else "Hayvon"
    return _push(
        call.vet.user,
        NotificationKind.CALL_NEW,
        "📥 Yangi chaqiruv",
        f"{label} · {pet}\n{call.note or ''}".strip(),
        call_request=call,
    )


def notify_call_status(call, actor):
    """
    Chaqiruv holati o'zgarganini qarama-qarshi tomonga bildiradi.
    Vet amal qilsa -> mijozga; mijoz bekor qilsa -> vetga.
    """
    if actor.id == call.vet.user_id:
        recipient = call.client
    else:
        recipient = call.vet.user
    return _push(
        recipient,
        NotificationKind.CALL_STATUS,
        "🔔 Chaqiruv holati",
        f"Holat: {call.get_status_display()}",
        call_request=call,
    )


# ----------------------- REJIM B: ServiceRequest/Offer -----------------------

def notify_new_tender(service_request):
    """Yangi tenderni mos vetlarga tarqatadi (fan-out Celery'da)."""
    fanout_tender.delay(service_request.pk)


def notify_new_offer(offer):
    """Mijozga yangi taklif kelganini bildiradi."""
    vet_name = offer.vet.user.get_full_name() or "Veterinar"
    return _push(
        offer.request.client,
        NotificationKind.OFFER_NEW,
        "💬 Yangi taklif",
        f"{vet_name} — {offer.price:g} so'm",
        service_request=offer.request,
        offer=offer,
    )


def notify_offer_accepted(offer):
    """Taklifi qabul qilingan vetga xabar beradi."""
    return _push(
        offer.vet.user,
        NotificationKind.OFFER_ACCEPTED,
        "✅ Taklifingiz qabul qilindi",
        f"Narx: {offer.price:g} so'm. Mijoz siz bilan bog'lanadi.",
        service_request=offer.request,
        offer=offer,
    )


def notify_offer_declined(offer):
    """Taklifi rad etilgan vetga xabar beradi."""
    return _push(
        offer.vet.user,
        NotificationKind.OFFER_DECLINED,
        "❌ Taklif rad etildi",
        "Mijoz boshqa taklifni tanladi.",
        service_request=offer.request,
        offer=offer,
    )


# ------------------------------- Izohlar -------------------------------

def notify_new_review(review):
    """Vetga yangi izoh qoldirilganini bildiradi."""
    return _push(
        review.vet.user,
        NotificationKind.REVIEW_NEW,
        "⭐ Yangi izoh",
        f"{review.stars}★ — {review.comment or 'izohsiz'}",
        call_request=review.request,
    )

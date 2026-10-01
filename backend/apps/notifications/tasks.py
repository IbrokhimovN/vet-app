"""
Bildirishnoma Celery vazifalari (ARCHITECTURE.md 7-bo'lim).

`deliver_notification` — bitta bildirishnomani Telegram'ga yetkazadi.
`fanout_tender`       — yangi tenderni mos vetlarga tarqatadi (fan-out).

Dev'da CELERY_TASK_ALWAYS_EAGER=True bo'lgani uchun vazifalar sinxron bajariladi.
"""
import html
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

# Bular doim muvaffaqiyatsiz bo'ladi (foydalanuvchi botni bloklagan, chat
# o'chirilgan va h.k.) — qayta urinish foyda bermaydi, darhol taslim bo'linadi.
_PERMANENT_ERROR_SUBSTRINGS = (
    "bot was blocked",
    "user is deactivated",
    "chat not found",
    "chat_id is empty",
    "bot can't initiate conversation",
    "peer_id_invalid",
    "bot was kicked",
)


def _is_permanent_error(message: str) -> bool:
    low = (message or "").lower()
    return any(s in low for s in _PERMANENT_ERROR_SUBSTRINGS)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def deliver_notification(self, notification_id):
    """
    Notification yozuvini Telegram'ga yuboradi va holatini yangilaydi.

    Vaqtinchalik xato (tarmoq, Telegram limiti) bo'lsa — eksponensial orqaga
    chekinish bilan max_retries martagacha qayta uriniladi. Doimiy xato (bot
    bloklangan va h.k.) bo'lsa — darhol taslim bo'linadi, qayta urinilmaydi.
    """
    from .models import Notification
    from .telegram import TelegramSendError, send_message

    try:
        n = Notification.objects.select_related("recipient").get(pk=notification_id)
    except Notification.DoesNotExist:
        return

    if n.is_sent:
        return

    chat_id = n.recipient.telegram_id
    if not chat_id:
        n.error = "Qabul qiluvchining telegram_id'si yo'q."
        n.save(update_fields=["error"])
        return

    # parse_mode=HTML: foydalanuvchi matnidagi "<", "&" Telegram'ni xabarni rad etishga majbur qilardi.
    title, body = html.escape(n.title or ""), html.escape(n.body or "")
    text = f"<b>{title}</b>\n{body}" if title else body
    try:
        send_message(n.bot, chat_id, text)
    except TelegramSendError as exc:
        n.error = str(exc)
        n.save(update_fields=["error"])
        if _is_permanent_error(str(exc)) or self.request.retries >= self.max_retries:
            logger.warning(
                "Bildirishnoma #%s butunlay muvaffaqiyatsiz (retries=%s): %s",
                n.pk, self.request.retries, exc,
            )
            return
        logger.info(
            "Bildirishnoma #%s yuborilmadi, qayta uriniladi (%s/%s): %s",
            n.pk, self.request.retries + 1, self.max_retries, exc,
        )
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))

    n.is_sent = True
    n.sent_at = timezone.now()
    n.error = ""
    n.save(update_fields=["is_sent", "sent_at", "error"])


@shared_task
def fanout_tender(service_request_id):
    """Yangi ochiq so'rovni mos (mutaxassislik + bo'sh) vetlarga tarqatadi."""
    from apps.requests.models import ServiceRequest, ServiceStatus
    from apps.vets.models import VetProfile
    from apps.vets.utils import region_q

    from .models import Notification, NotificationKind

    try:
        sr = ServiceRequest.objects.select_related("specialization").get(
            pk=service_request_id
        )
    except ServiceRequest.DoesNotExist:
        return
    if sr.status != ServiceStatus.OPEN:
        return

    vets = VetProfile.objects.filter(
        is_available=True, user__telegram_id__isnull=False
    ).select_related("user")
    if sr.specialization_id:
        vets = vets.filter(specializations=sr.specialization_id)
    if sr.city:
        vets = vets.filter(region_q("city", sr.city))

    spec = sr.specialization.name if sr.specialization else "Umumiy"
    title = "📢 Yangi tender"
    body = (
        f"{spec} · {sr.city or '—'}\n"
        f"{sr.note or 'Izoh yo‘q'}"
    )
    for vet in vets.iterator():
        n = Notification.objects.create(
            recipient=vet.user,
            kind=NotificationKind.TENDER_NEW,
            title=title,
            body=body,
            bot="vet",
            service_request=sr,
        )
        deliver_notification.delay(n.pk)

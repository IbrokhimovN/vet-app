"""
Davriy vazifalar (Celery beat, config/celery.py'dagi beat_schedule orqali
chaqiriladi) — pilot uchun aniqlangan kamchilik: javobsiz chaqiruv abadiy
"Kutilmoqda"da qolib ketmasligi kerak.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def expire_unanswered_calls():
    """
    `CALL_RESPONSE_TIMEOUT_MINUTES` daqiqadan beri PENDING turgan to'g'ridan
    chaqiruvlarni EXPIRED'ga o'tkazadi va ikkala tomonga xabar beradi.

    Har bir yozuv alohida, qulflab (`select_for_update`) yopiladi — shu bilan
    vet aynan shu payt "qabul qilish" tugmasini bossa, poyga holati (race)
    oldini olinadi: kim birinchi bo'lib DB qatorini qulflasa, o'sha g'olib.
    """
    from apps.notifications import services as notify

    from .models import CallRequest, CallStatus

    cutoff = timezone.now() - timedelta(minutes=settings.CALL_RESPONSE_TIMEOUT_MINUTES)
    stale_ids = list(
        CallRequest.objects.filter(status=CallStatus.PENDING, created_at__lte=cutoff)
        .values_list("id", flat=True)
    )
    expired = []
    for call_id in stale_ids:
        with transaction.atomic():
            try:
                call = CallRequest.objects.select_for_update().get(pk=call_id)
            except CallRequest.DoesNotExist:
                continue
            # Qulfni olguncha vet ulgurib qabul/rad qilgan yoki mijoz bekor qilgan bo'lishi mumkin.
            if call.status != CallStatus.PENDING:
                continue
            # responded_at ataylab qo'yilmaydi — u "vet haqiqatan javob berdi"
            # degani, statistikadagi "javob tezligi" shunga asoslanadi (adminpanel).
            call.status = CallStatus.EXPIRED
            call.save(update_fields=["status", "updated_at"])
            expired.append(call)

    for call in expired:
        notify.notify_call_expired(call)

    if expired:
        logger.info("expire_unanswered_calls: %s ta chaqiruv muddati tugadi deb belgilandi", len(expired))
    return len(expired)

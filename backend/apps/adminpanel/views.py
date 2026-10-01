"""
Admin panel view'lari — alohida statik front (/admin-panel/) shu API'ga ulanadi.

Xavfsizlik: barcha ro'yxat/amal view'lari IsAdminUser (faqat is_staff=True)
bilan himoyalangan. Login esa AllowAny — lekin faqat is_staff foydalanuvchiga
JWT beradi, boshqalarga 403 qaytaradi.
"""
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth import authenticate
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Role, User
from apps.moderation.models import Report
from apps.notifications.models import Notification
from apps.notifications.tasks import deliver_notification
from apps.requests.models import CallRequest, CallStatus, Offer, ServiceRequest, ServiceStatus
from apps.reviews.models import Review
from apps.vets.models import Clinic, VetProfile

from .serializers import (
    AdminCallSerializer,
    AdminClinicSerializer,
    AdminNotificationSerializer,
    AdminReportSerializer,
    AdminReviewSerializer,
    AdminServiceRequestSerializer,
    AdminUserSerializer,
    AdminVetSerializer,
)


class AdminLoginView(APIView):
    """POST /admin/login/ — username+parol, faqat is_staff uchun JWT qaytaradi."""

    permission_classes = [AllowAny]
    # Parolni taxmin qilib urinishdan (brute-force) himoya.
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "admin-login"

    def post(self, request):
        username = request.data.get("username", "")
        password = request.data.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_staff:
            return Response(
                {"detail": "Login yoki parol noto'g'ri, yoki admin huquqi yo'q."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.get_full_name() or user.username,
                "is_superuser": user.is_superuser,
            },
        })


class DashboardStatsView(APIView):
    """GET /admin/stats/ — bosh sahifa uchun umumiy ko'rsatkichlar."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        today = timezone.now().date()
        since = timezone.now() - timedelta(days=30)

        # --- "Javob tezligi" (pilot KPI): so'nggi 30 kunda javob berilgan
        # chaqiruvlarning o'rtacha (created_at -> responded_at) daqiqasi.
        responded = CallRequest.objects.filter(
            responded_at__isnull=False, created_at__gte=since
        ).annotate(
            wait=ExpressionWrapper(F("responded_at") - F("created_at"), output_field=DurationField())
        )
        avg_wait = responded.aggregate(v=Avg("wait"))["v"]
        avg_response_minutes = round(avg_wait.total_seconds() / 60, 1) if avg_wait else None

        # --- "Yakunlanish ulushi": so'nggi 30 kunda tugagan (yakunlangan/rad/bekor/
        # muddati tugagan) chaqiruvlarning necha foizi COMPLETED bilan tugagan.
        finished_statuses = [CallStatus.COMPLETED, CallStatus.REJECTED, CallStatus.CANCELLED, CallStatus.EXPIRED]
        finished = CallRequest.objects.filter(created_at__gte=since, status__in=finished_statuses)
        finished_total = finished.count()
        finished_completed = finished.filter(status=CallStatus.COMPLETED).count()
        completion_rate = round(100 * finished_completed / finished_total, 1) if finished_total else None

        # --- "Tender faolligi": so'nggi 30 kunda yaratilgan ochiq so'rovga
        # o'rtacha nechta taklif kelgan.
        tenders_30d = ServiceRequest.objects.filter(created_at__gte=since).count()
        offers_30d = Offer.objects.filter(request__created_at__gte=since).count()
        avg_offers_per_tender = round(offers_30d / tenders_30d, 1) if tenders_30d else None

        # --- Yetkazib bo'lmagan bildirishnomalar (10-bo'lim: avval bu ko'rinmas edi).
        failed_notifications = Notification.objects.filter(is_sent=False).exclude(error="").count()

        return Response({
            "total_clients": User.objects.filter(role=Role.CLIENT).count(),
            "total_vets": User.objects.filter(role=Role.VET).count(),
            "verified_vets": VetProfile.objects.filter(is_verified=True).count(),
            "unverified_vets": VetProfile.objects.filter(is_verified=False).count(),
            "active_calls": CallRequest.objects.filter(
                status__in=[CallStatus.PENDING, CallStatus.ACCEPTED, CallStatus.ON_WAY]
            ).count(),
            "completed_calls": CallRequest.objects.filter(status=CallStatus.COMPLETED).count(),
            "open_tenders": ServiceRequest.objects.filter(status=ServiceStatus.OPEN).count(),
            "calls_today": CallRequest.objects.filter(created_at__date=today).count(),
            "total_reviews": Review.objects.count(),
            "unresolved_reports": Report.objects.filter(is_resolved=False).count(),
            # Pilot KPI'lari (10-bo'lim) — 30 kunlik oyna, yetarli ma'lumot bo'lmasa null.
            "avg_response_minutes": avg_response_minutes,
            "completion_rate": completion_rate,
            "avg_offers_per_tender": avg_offers_per_tender,
            "failed_notifications": failed_notifications,
        })


class AdminUserListView(generics.ListAPIView):
    """GET /admin/users/?role=&q= — barcha foydalanuvchilar."""

    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = User.objects.all().order_by("-date_joined")
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(username__icontains=q) | Q(first_name__icontains=q)
                | Q(last_name__icontains=q) | Q(phone__icontains=q)
            )
        return qs


class AdminUserToggleActiveView(APIView):
    """POST /admin/users/<id>/toggle-active/ — bloklash / blokdan chiqarish."""

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        user = generics.get_object_or_404(User, pk=pk)
        if user.is_superuser:
            return Response({"detail": "Superuser'ni bloklab bo'lmaydi."}, status=400)
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        return Response({"id": user.id, "is_active": user.is_active})


class AdminUserDeleteView(generics.DestroyAPIView):
    """
    DELETE /admin/users/<id>/ — foydalanuvchini butunlay o'chiradi.

    Diqqat: qaytarib bo'lmaydi. Bog'liq yozuvlar (VetProfile, chaqiruvlar,
    izohlar, shikoyatlar, bildirishnomalar) modelda CASCADE bo'lgani uchun
    ular ham birga o'chadi — boshqa tomon (masalan, mijoz o'chirilgan vetning
    tarixi) tegishli yozuvlarini ham yo'qotishi mumkin. Shaxsiy ma'lumotlarni
    o'chirish huquqi (11-bo'lim, Maxfiylik siyosati) uchun kerak.
    """

    permission_classes = [IsAdminUser]
    queryset = User.objects.all()

    def perform_destroy(self, instance):
        if instance.is_superuser:
            raise ValidationError("Superuser'ni o'chirib bo'lmaydi.")
        instance.delete()


class AdminVetListView(generics.ListAPIView):
    """GET /admin/vets/?verified=&q= — barcha veterinarlar."""

    serializer_class = AdminVetSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = VetProfile.objects.select_related("user", "clinic").prefetch_related("specializations").order_by("-created_at")
        verified = self.request.query_params.get("verified")
        if verified == "1":
            qs = qs.filter(is_verified=True)
        elif verified == "0":
            qs = qs.filter(is_verified=False)
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(user__username__icontains=q) | Q(user__first_name__icontains=q)
                | Q(clinic_name__icontains=q) | Q(city__icontains=q)
            )
        return qs


class AdminVetToggleVerifyView(APIView):
    """POST /admin/vets/<id>/toggle-verify/ — tasdiqlash / bekor qilish."""

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        vet = generics.get_object_or_404(VetProfile, pk=pk)
        vet.is_verified = not vet.is_verified
        vet.save(update_fields=["is_verified"])
        return Response({"id": vet.id, "is_verified": vet.is_verified})


class AdminVetToggleTopView(APIView):
    """
    POST /admin/vets/<id>/toggle-top/ — {"days": 7} (ixtiyoriy, sukut 7).
    Pilotda to'lov Payme/Click integratsiyasisiz, qo'lda (bank o'tkazmasi va
    h.k.) qabul qilinadi (12-bo'lim) — admin shu yerdan TOP joylashuvni yoqadi.
    Avval buning uchun panel yo'q edi (10-bo'lim: pilotda aniqlangan kamchilik).
    """

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        vet = generics.get_object_or_404(VetProfile, pk=pk)
        vet.is_top = not vet.is_top
        if vet.is_top:
            try:
                days = int(request.data.get("days", 7))
            except (TypeError, ValueError):
                return Response({"detail": "days butun son bo'lishi kerak."}, status=400)
            if days <= 0:
                return Response({"detail": "days musbat bo'lishi kerak."}, status=400)
            vet.top_until = timezone.now() + timedelta(days=days)
        else:
            vet.top_until = None
        vet.save(update_fields=["is_top", "top_until"])
        return Response({"id": vet.id, "is_top": vet.is_top, "top_until": vet.top_until})


class AdminVetWalletAdjustView(APIView):
    """
    POST /admin/vets/<id>/wallet-adjust/ — {"amount": "50000"} (manfiy ham mumkin).
    Qo'lda to'lovni (yoki tuzatishni) hamyon balansiga yozib qo'yish uchun.
    """

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        vet = generics.get_object_or_404(VetProfile, pk=pk)
        try:
            amount = Decimal(str(request.data.get("amount", "")))
        except (InvalidOperation, TypeError):
            return Response({"detail": "amount to'g'ri son bo'lishi kerak."}, status=400)
        new_balance = vet.wallet_balance + amount
        if new_balance < 0:
            return Response({"detail": "Balans manfiy bo'lishi mumkin emas."}, status=400)
        vet.wallet_balance = new_balance
        vet.save(update_fields=["wallet_balance"])
        return Response({"id": vet.id, "wallet_balance": vet.wallet_balance})


class AdminCallListView(generics.ListAPIView):
    """GET /admin/calls/?status= — barcha to'g'ridan chaqiruvlar."""

    serializer_class = AdminCallSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = CallRequest.objects.select_related("client", "vet__user", "pet").order_by("-created_at")
        st = self.request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)
        return qs


class AdminServiceRequestListView(generics.ListAPIView):
    """GET /admin/tenders/?status= — barcha ochiq so'rovlar (tender)."""

    serializer_class = AdminServiceRequestSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = ServiceRequest.objects.select_related("client", "specialization").order_by("-created_at")
        st = self.request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)
        return qs


class AdminReviewListView(generics.ListAPIView):
    """GET /admin/reviews/ — barcha izohlar."""

    serializer_class = AdminReviewSerializer
    permission_classes = [IsAdminUser]
    queryset = Review.objects.select_related("client", "vet__user").order_by("-created_at")


class AdminReviewDeleteView(generics.DestroyAPIView):
    """DELETE /admin/reviews/<id>/ — nomaqbul izohni o'chirish."""

    permission_classes = [IsAdminUser]
    queryset = Review.objects.all()


class AdminReportListView(generics.ListAPIView):
    """GET /admin/reports/?resolved= — barcha shikoyatlar."""

    serializer_class = AdminReportSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = Report.objects.select_related("reporter", "reported_user").order_by("is_resolved", "-created_at")
        resolved = self.request.query_params.get("resolved")
        if resolved == "1":
            qs = qs.filter(is_resolved=True)
        elif resolved == "0":
            qs = qs.filter(is_resolved=False)
        return qs


class AdminReportResolveView(APIView):
    """POST /admin/reports/<id>/resolve/ — ko'rib chiqilgan deb belgilash."""

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        report = generics.get_object_or_404(Report, pk=pk)
        report.is_resolved = True
        report.save(update_fields=["is_resolved"])
        return Response({"id": report.id, "is_resolved": report.is_resolved})


class AdminNotificationListView(generics.ListAPIView):
    """
    GET /admin/notifications/?failed=1 — bildirishnoma yetkazish holati
    (10-bo'lim: pilotda aniqlangan kamchilik — avval buni ko'rish imkoni yo'q edi).
    """

    serializer_class = AdminNotificationSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = Notification.objects.select_related("recipient").order_by("-created_at")
        if self.request.query_params.get("failed") == "1":
            qs = qs.filter(is_sent=False).exclude(error="")
        return qs


class AdminNotificationRetryView(APIView):
    """POST /admin/notifications/<id>/retry/ — muvaffaqiyatsiz bildirishnomani qayta yuborishga urinadi."""

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        notification = generics.get_object_or_404(Notification, pk=pk)
        if notification.is_sent:
            return Response({"detail": "Bu bildirishnoma allaqachon yetkazilgan."}, status=400)
        notification.error = ""
        notification.save(update_fields=["error"])
        deliver_notification.delay(notification.pk)
        return Response({"id": notification.id, "queued": True})


class AdminClinicListCreateView(generics.ListCreateAPIView):
    """GET/POST /admin/clinics/?verified=&q= — klinikalar (1-bosqich: faqat admin qo'shadi)."""

    serializer_class = AdminClinicSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = Clinic.objects.prefetch_related("specializations", "vets__user").order_by("-created_at")
        verified = self.request.query_params.get("verified")
        if verified == "1":
            qs = qs.filter(is_verified=True)
        elif verified == "0":
            qs = qs.filter(is_verified=False)
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(city__icontains=q) | Q(address__icontains=q) | Q(phone__icontains=q))
        return qs


class AdminClinicDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /admin/clinics/<id>/ — o'chirilganda vetlar klinikasiz qoladi (SET_NULL)."""

    serializer_class = AdminClinicSerializer
    permission_classes = [IsAdminUser]
    queryset = Clinic.objects.prefetch_related("specializations", "vets__user")


class AdminClinicToggleVerifyView(APIView):
    """POST /admin/clinics/<id>/toggle-verify/ — mijozlarga faqat tasdiqlangani ko'rinadi."""

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        clinic = generics.get_object_or_404(Clinic, pk=pk)
        clinic.is_verified = not clinic.is_verified
        clinic.save(update_fields=["is_verified"])
        return Response({"id": clinic.id, "is_verified": clinic.is_verified})


class AdminVetSetClinicView(APIView):
    """POST /admin/vets/<id>/set-clinic/ — {"clinic": <id> | null}."""

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        vet = generics.get_object_or_404(VetProfile, pk=pk)
        clinic_id = request.data.get("clinic")
        if clinic_id in (None, "", 0, "0"):
            vet.clinic = None
        else:
            try:
                vet.clinic = Clinic.objects.get(pk=int(clinic_id))
            except (Clinic.DoesNotExist, TypeError, ValueError):
                return Response({"detail": "Bunday klinika topilmadi."}, status=400)
            vet.clinic_name = vet.clinic.name
        vet.save(update_fields=["clinic", "clinic_name"])
        return Response({"id": vet.id, "clinic": vet.clinic_id})

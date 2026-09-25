"""
So'rov yaratishga xos tezlik cheklovlari (10-bo'lim: pilotda aniqlangan
kamchilik — avval faqat umumiy 300/min bor edi, spam yaratishga xos limit yo'q edi).

`ScopedRateThrottle` butun view'ga (GET + POST) tegadi — bu esa "So'rovlarim"
ro'yxatini tez-tez yangilab turadigan (pull-to-refresh) foydalanuvchiga
to'sqinlik qilardi. Shu klass faqat POST (yaratish)ga tegadi.
"""
from rest_framework.throttling import ScopedRateThrottle


class CreateOnlyRateThrottle(ScopedRateThrottle):
    def allow_request(self, request, view):
        if request.method != "POST":
            return True
        return super().allow_request(request, view)

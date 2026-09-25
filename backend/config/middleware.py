"""
Telegram Mini App middleware.

Mini App sahifalari (/client/, /vet/) Telegram WebView ichida ochiladi.
Django standart XFrameOptionsMiddleware 'X-Frame-Options: DENY' qo'yadi,
bu esa WebView'ni bloklaydi. Shu middleware Mini App yo'llarida
bu headerni olib tashlaydi.
"""


class TelegramMiniAppMiddleware:
    """Mini App yo'llarida X-Frame-Options va COOP headerlarini olib tashlaydi."""

    MINI_APP_PREFIXES = ("/client/", "/vet/")
    HEADERS_TO_REMOVE = ("X-Frame-Options", "Cross-Origin-Opener-Policy")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(self.MINI_APP_PREFIXES):
            for header in self.HEADERS_TO_REMOVE:
                try:
                    del response[header]
                except KeyError:
                    pass
        return response

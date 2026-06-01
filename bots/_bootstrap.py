"""
Botlar Django jarayonidan tashqarida (standalone) ishlaydi, lekin token va
Mini App URL kabi sozlamalarni bir joydan — Django `settings`'dan oladi.

Bu modul import qilinishi bilan Django sozlamalari yuklanadi. Botlar shu
moduldan birinchi bo'lib import qiladi:

    from bots import _bootstrap  # noqa: F401
    from django.conf import settings
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

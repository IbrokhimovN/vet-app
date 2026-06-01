"""Reyting qayta hisoblash xizmati (ARCHITECTURE.md 4.2)."""
from decimal import Decimal

from django.db.models import Avg, Count


def recompute_vet_rating(vet):
    """Vetning izohlaridan rating_avg/rating_count'ni qayta hisoblab saqlaydi."""
    agg = vet.reviews.aggregate(avg=Avg("stars"), cnt=Count("id"))
    avg = agg["avg"] or 0
    vet.rating_avg = Decimal(str(round(avg, 2)))
    vet.rating_count = agg["cnt"]
    vet.save(update_fields=["rating_avg", "rating_count"])

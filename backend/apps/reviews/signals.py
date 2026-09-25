"""Izoh saqlanganda/o'chirilganda vet reytingini yangilab turadi."""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Review
from .services import recompute_vet_rating


@receiver(post_save, sender=Review)
def review_saved(sender, instance, **kwargs):
    recompute_vet_rating(instance.vet)


@receiver(post_delete, sender=Review)
def review_deleted(sender, instance, **kwargs):
    recompute_vet_rating(instance.vet)

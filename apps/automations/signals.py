from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.crm.models import Lead
from .services import send_lead_created_webhook


@receiver(post_save, sender=Lead)
def lead_created_webhook(sender, instance, created, **kwargs):
    if not created:
        return
    if not getattr(settings, "GDC_AUTOMATIONS_ENABLED", False):
        return
    send_lead_created_webhook(instance)

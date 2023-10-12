from django.conf import settings
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.urls import reverse

from .models import Service, ServiceTranslation


@receiver(pre_save, sender=Service)
def default_url(sender, instance, **kwargs):
    path = reverse('service_detail', args=[instance.slug])
    if not instance.url:
        instance.url = (f"{settings.PROTOCOL}://{settings.HOST}"
                        f"/en{path[path.find('/services'):]}")


@receiver(pre_save, sender=ServiceTranslation)
def default_url_translation(sender, instance, **kwargs):
    path = reverse('service_detail', args=[instance.service.slug])
    if not instance.url:
        instance.url = (f"{settings.PROTOCOL}://{settings.HOST}"
                        f"/{instance.language}{path[path.find('/services'):]}")

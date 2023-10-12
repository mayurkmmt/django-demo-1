from django.contrib import admin

from .models import Transport
from .models import DeliveryService
from .models import DeliveryArea
from .models import DeliverySlot


@admin.register(DeliverySlot)
class DeliverySlotAdmin(admin.ModelAdmin):
    list_display = ['area', 'postal_code_range_start', 'postal_code_range_end']


@admin.register(DeliveryArea)
class DeliveryAreaAdmin(admin.ModelAdmin):
    pass


@admin.register(Transport)
class TransportAdmin(admin.ModelAdmin):
    pass


@admin.register(DeliveryService)
class DeliveryServiceAdmin(admin.ModelAdmin):
    pass

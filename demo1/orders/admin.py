from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from django_fsm_log.admin import StateLogInline
from fsm_admin.mixins import FSMTransitionMixin

from .models import Order
from .models import OrderUnit
from .models import OrderGroup
from .models import OrderDeliverySlot
from .models import Payment
from .models import PromotionalCode


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    pass


@admin.register(OrderDeliverySlot)
class OrderDeliverySlotAdmin(admin.ModelAdmin):
    pass


@admin.register(OrderUnit)
class OrderUnitAdmin(admin.ModelAdmin):
    pass


class OrderDeliverySlotInline(admin.StackedInline):
    model = OrderDeliverySlot
    fields = ['date', 'slot_start', 'slot_end']
    readonly_fields = ['date', 'slot_start', 'slot_end']

    def slot_start(self, obj=None):
        if obj is not None and obj.pk:
            return obj.slot.slot_start
        return '-'
    slot_start.short_description = 'Start'

    def slot_end(self, obj=None):
        if obj is not None and obj.pk:
            return obj.slot.slot_end
        return '-'
    slot_end.short_description = 'End'


class OrderUnitInline(admin.TabularInline):
    model = OrderUnit


@admin.register(OrderGroup)
class OrderGroupAdmin(admin.ModelAdmin):
    fields = ['order_link', 'order']
    readonly_fields = ['order_link']
    model = OrderGroup
    inlines = [OrderUnitInline]

    def order_link(self, obj=None):
        if obj is not None and obj.pk:
            url = reverse(f'admin:orders_order_change', args=[obj.order.pk])
            return mark_safe(f'<a href="{url}">View order</a>')
        return '-'
    order_link.short_description = 'Order'


class OrderGroupInline(admin.StackedInline):
    fields = ['created_at', 'service_count', 'edit_group']
    readonly_fields = ['created_at', 'edit_group', 'service_count']
    model = OrderGroup
    extra = 0

    def edit_group(self, obj=None):
        if obj is not None and obj.pk:
            url = reverse('admin:orders_ordergroup_change', args=[obj.pk])
            return mark_safe(f'<a href="{url}">View or edit this group</a>')
        return '-'
    edit_group.short_description = 'Edit'

    def service_count(self, obj=None):
        if obj is not None and obj.pk:
            services = [unit.service.name for unit in obj.services.all()]
            return ', '.join(services)
        return '-'
    service_count.short_description = 'Services'


@admin.register(Order)
class OrderAdmin(FSMTransitionMixin, admin.ModelAdmin):
    list_display = [
        'order_id',
        'last_name',
        'state',
        'no_printer',
        'created_at',
    ]
    readonly_fields = ['state', 'code', 'no_printer']
    search_fields = ['first_name', 'last_name']
    date_hierarchy = 'created_at'
    list_filter = ['state']
    inlines = [OrderDeliverySlotInline, OrderGroupInline, StateLogInline]


@admin.register(PromotionalCode)
class PromotionalCodeAdmin(admin.ModelAdmin):
    list_display = [
        'code',
        'expiration',
        'activations',
    ]

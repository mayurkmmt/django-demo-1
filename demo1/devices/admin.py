from django.contrib import admin

from .models import Brand
from .models import ProductFamily
from .models import Device
from .models import DeviceService


class DeviceServiceInline(admin.TabularInline):
    model = DeviceService


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['product_family', 'name', 'product_type', 'priority']
    list_filter = ['product_family', 'product_family__brand', 'product_type']
    list_editable = [
        'priority',
    ]
    inlines = [DeviceServiceInline]
    prepopulated_fields = {'slug': ['name']}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'priority']
    list_editable = [
        'priority',
    ]
    prepopulated_fields = {'slug': ['name']}


@admin.register(ProductFamily)
class ProductFamilyAdmin(admin.ModelAdmin):
    list_display = ['brand', 'name', 'priority']
    list_filter = ['brand']
    list_editable = [
        'priority',
    ]
    prepopulated_fields = {'slug': ['name']}


@admin.register(DeviceService)
class DeviceServiceAdmin(admin.ModelAdmin):
    list_display = [
        'device',
        'service',
        'price',
    ]
    list_filter = ['device']
    list_editable = [
        'price',
    ]

from django.contrib import admin

from .models import Service
from .models import ServiceTranslation


class ServiceTranslationInline(admin.StackedInline):
    model = ServiceTranslation


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    inlines = [ServiceTranslationInline]
    prepopulated_fields = {'slug': ['name']}
    list_display = [
        'name',
        'category',
        'priority',
    ]
    list_editable = [
        'priority',
    ]

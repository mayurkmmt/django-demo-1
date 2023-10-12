from django.db import models

from ..services.models import Service


class Brand(models.Model):
    name = models.CharField(max_length=30)
    slug = models.SlugField(help_text="Unique URL-friendly version of name.")

    icon = models.FileField(blank=True, upload_to='brands')

    priority = models.DecimalField(max_digits=5, decimal_places=2, default=0.0,
                                   help_text=("Prioritize display ordering."))

    class Meta:
        ordering = ['priority', 'name']

    def __str__(self):
        return self.name


class ProductFamily(models.Model):
    brand = models.ForeignKey(Brand, related_name='product_families',
                              on_delete=models.PROTECT)
    name = models.CharField(max_length=30)
    slug = models.SlugField(help_text="Unique URL-friendly version of name.")

    icon = models.FileField(blank=True, upload_to='product-families')

    priority = models.DecimalField(max_digits=5, decimal_places=2, default=0.0,
                                   help_text=("Prioritize display ordering."))

    class Meta:
        verbose_name_plural = 'product families'
        ordering = ['priority', 'name']

    def __str__(self):
        return f'{self.brand} {self.name}'


class Device(models.Model):
    SMARTPHONE = 'smartphone'
    TABLET = 'tablet'

    product_family = models.ForeignKey(ProductFamily, related_name='devices',
                                       on_delete=models.CASCADE)
    product_type = models.CharField(max_length=20, choices=(
        (SMARTPHONE, 'Smartphone'),
        (TABLET, 'Tablet'),
    ), default=SMARTPHONE)

    name = models.CharField(max_length=30)
    slug = models.SlugField(help_text="Unique URL-friendly version of name.")

    icon = models.FileField(blank=True, upload_to='devices', help_text=(
        "The icon, if there is one, of the product family will be used if you "
        "do not add an icon to this device."
    ))

    priority = models.DecimalField(max_digits=5, decimal_places=2, default=0.0,
                                   help_text=("Prioritize display ordering."))

    class Meta:
        ordering = ['priority', 'name']

    def __str__(self):
        return self.name


class DeviceService(models.Model):
    device = models.ForeignKey(Device, related_name='services',
                               on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=0, default=0.0)
    currency = models.CharField(max_length=10, choices=(
        ('SEK', ' kr'),
    ), default='SEK')

    class Meta:
        unique_together = ('device', 'service')
        ordering = ['service__priority']

    def __str__(self):
        return f'{self.service.name} {self.device.name}'

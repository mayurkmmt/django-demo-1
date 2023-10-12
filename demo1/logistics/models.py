from django.core.validators import RegexValidator
from django.db import models
from django_countries.fields import CountryField

LengthValidator = RegexValidator(
    regex="^.{5}$",
    message="Postal codes must be exact 5 characters long.",
    code="nomatch",
)


class DeliveryService(models.Model):
    """A company that provides delivery services."""

    name = models.CharField(max_length=200)

    email = models.EmailField()
    phone = models.CharField(max_length=100, blank=True)

    address = models.TextField()
    address_extra = models.TextField(blank=True)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=100)
    country = CountryField()

    def __str__(self):
        return self.name


class Transport(models.Model):
    """Transport of an order."""

    CUSTOMER = "customer"
    SHOP = "shop"
    BOTH = "both"

    service = models.ForeignKey(DeliveryService, on_delete=models.CASCADE)
    direction = models.CharField(
        max_length=20,
        choices=(
            (CUSTOMER, "Customer"),
            (SHOP, "Shop"),
            (BOTH, "Both ways"),
        ),
    )

    tracking_code = models.CharField(max_length=200, blank=True)
    tracking_url = models.URLField(blank=True)

    ordered_at = models.DateTimeField(auto_now_add=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.service} -> {self.direction}"


class DeliveryArea(models.Model):
    """An intermediary model used to group `DeliverySlots`."""

    service = models.ForeignKey(DeliveryService, on_delete=models.CASCADE)
    name = models.CharField(
        max_length=100, help_text=("Name of the region, e.g. Malaga")
    )

    def __str__(self):
        return f"{self.service} - {self.name}"


class DeliverySlot(models.Model):
    area = models.ForeignKey(DeliveryArea, on_delete=models.CASCADE)

    postal_code_range_start = models.CharField(
        max_length=5,
        validators=[LengthValidator],
    )
    postal_code_range_end = models.CharField(
        max_length=5,
        blank=True,
        validators=[LengthValidator],
        help_text=(
            "If an end value is present the start and end is considered a "
            "range and any postal code within that range (inclusive) is "
            "considered a match."
        ),
    )

    slot_start = models.TimeField()
    slot_end = models.TimeField()

    margin = models.IntegerField(
        default=90,
        help_text=(
            "Orders may be placed only if placed before the slot end time minus "
            "the margin"
        ),
    )

    mon = models.BooleanField(default=True)
    tue = models.BooleanField(default=True)
    wed = models.BooleanField(default=True)
    thu = models.BooleanField(default=True)
    fri = models.BooleanField(default=True)
    sat = models.BooleanField(default=False)
    sun = models.BooleanField(default=False)

    def day_indices(self):
        days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        return [index for index in range(0, len(days)) if getattr(self, days[index])]

    def __str__(self):
        return f"{self.area.name} {self.postal_code_range_start}"

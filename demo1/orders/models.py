import datetime
import decimal
import os
import uuid

import stripe
from django.conf import settings
from django.core.mail import send_mail
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone
from django_countries.fields import CountryField
from django_fsm import RETURN_VALUE, FSMField, transition

from ..devices.models import Device, DeviceService
from ..logistics.models import DeliverySlot, Transport
from ..shops.models import Shop

ORDER_NUMBER_OFFSET = 1000


def _send_mail(to, subject, template, context=None):
    to = to if isinstance(to, list) else [to]
    if settings.SEND_EMAILS:
        template = os.path.join("emails", f"{template}.txt")
        msg = render_to_string(template, context)
        subject = f"[demo1] {subject}"
        send_mail(
            subject=subject,
            message=msg,
            from_email=settings.FROM_EMAIL,
            recipient_list=to,
        )


def get_expiration(days=30):
    return timezone.now() + timezone.timedelta(days=30)


class PromotionalCode(models.Model):
    code = models.CharField(
        max_length=50,
        validators=[
            RegexValidator(
                regex="^[A-Z0-9-]+$",
                message=(
                    "Promo code should only contain uppercase letters, numbers "
                    "and dashes"
                ),
            )
        ],
    )
    expiration = models.DateTimeField(default=get_expiration)
    max_activations = models.IntegerField(
        default=0,
        help_text=(
            "Use to limit the number of times that this promotional code can "
            "be activated. Default is 0 (unlimited)."
        ),
    )
    activations = models.IntegerField(default=0, editable=False)
    discount_percent = models.IntegerField(
        null=True,
        blank=True,
        help_text=(
            "Percentage discount 1 - 100" '(e.g. enter "10" for a 10 percent discount.'
        ),
        validators=[MinValueValidator(1), MaxValueValidator(100)],
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=("Currency formatted discount."),
    )


class Order(models.Model):
    state = FSMField(default="pending")
    code = models.UUIDField(default=uuid.uuid4, editable=False)

    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)

    email = models.EmailField()

    allow_marketing = models.NullBooleanField()
    phone = models.CharField(max_length=100, blank=True)
    address = models.TextField()
    address_extra = models.TextField(blank=True)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=100)
    country = CountryField()

    unlock_code = models.CharField(max_length=50, blank=True)
    no_printer = models.BooleanField(default=False)

    preferred_language = models.CharField(
        max_length=5,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE,
    )

    device = models.ForeignKey(Device, on_delete=models.PROTECT)

    promo_code = models.ForeignKey(
        PromotionalCode, null=True, on_delete=models.SET_NULL
    )
    discount_percent = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    shop = models.ForeignKey(
        Shop,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    transport_to_shop = models.ForeignKey(
        Transport,
        on_delete=models.PROTECT,
        related_name="to_shop_orders",
        null=True,
        blank=True,
    )
    transport_to_customer = models.ForeignKey(
        Transport,
        on_delete=models.PROTECT,
        related_name="to_customer_orders",
        null=True,
        blank=True,
    )

    current_order = models.ForeignKey(
        "OrderGroup",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="current_order_for",
    )
    reviewed_order = models.ForeignKey(
        "OrderGroup",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="review_for",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def order_id(self):
        m = 100000000
        x = 387420489
        encoded = self.pk * x % m
        return f"{encoded}"

    @property
    def total_payments(self):
        return sum([payment.amount for payment in self.payments.filter(status="paid")])

    @property
    def total_price(self):
        if self.current_order is None:
            return 0

        total = self.current_order.total
        if self.discount_percent:
            total = total - (total * self.discount_percent / 100)
        if self.discount_amount:
            total = total - self.discount_amount

        return total + decimal.Decimal(settings.SHIPMENT_FEE)

    @property
    def amount_to_pay(self):
        return self.total_price - self.total_payments

    def create_pending_payments(self):
        payment = self.payments.create(
            amount=self.amount_to_pay,
        )

        if settings.STRIPE_ENABLED:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            intent = stripe.PaymentIntent.create(
                amount=round(self.amount_to_pay * 100),
                currency="sek",
                receipt_email=self.email,
                metadata={
                    "order_id": self.id,
                    "payment_id": payment.id,
                },
            )
            payment.payment_reference = intent.client_secret
            payment.save()

    def has_been_paid(self):
        return self.amount_to_pay <= 0

    def has_been_repaired(self):
        return not OrderUnit.objects.filter(
            group__order=self, repaired_at__isnull=True
        ).exists()

    def has_shop(self):
        return self.shop is not None

    def has_transport_to_shop(self):
        return self.transport_to_shop is not None

    def has_transport_to_customer(self):
        return self.transport_to_customer is not None

    def has_review(self):
        return self.reviewed_order is not None

    def send_mail(self, subject):
        _send_mail(
            self.email,
            subject,
            "standard",
            {
                "order": self,
                "site_url": settings.SITE_URL,
                "subject": subject,
            },
        )

    def send_staff_mail(self, subject):
        _send_mail(
            settings.STAFF_MAIL,
            subject,
            "standard",
            {
                "order": self,
                "site_url": settings.SITE_URL,
                "subject": subject,
            },
        )

    # State transitions

    @transition(
        field=state,
        source="pending",
        target="needs-payment",
    )
    def register_payment_intent(self):
        self.updated_at = timezone.now()
        # self.send_mail('Order received')

        if self.amount_to_pay > 0:
            self.create_pending_payments()

        return "needs-payment"

    @transition(
        field=state,
        source=["needs-payment", "needs-extra-payment"],
        target=RETURN_VALUE("ready-for-repair", "paid"),
        conditions=[has_been_paid],
    )
    def mark_as_paid(self):
        self.updated_at = timezone.now()
        if self.state == "needs-payment":
            self.send_mail("Payment received")
            self.send_staff_mail("New order received")
            return "paid"
        return "ready-for-repair"

    @transition(
        field=state,
        source=["pending", "needs-payment"],
        target="cancelled",
    )
    def cancel(self):
        self.updated_at = timezone.now()
        self.save()

    @transition(
        field=state,
        source="paid",
        target="assigned-to-shop",
        conditions=[has_shop],
    )
    def assigned_to_shop(self):
        self.updated_at = timezone.now()
        self.save()

    @transition(
        field=state,
        source="assigned-to-shop",
        target="transport-to-shop-requested",
        conditions=[has_transport_to_shop],
    )
    def transport_to_shop_requested(self):
        self.send_mail("Transport requested")
        self.updated_at = timezone.now()
        self.save()

    @transition(
        field=state,
        source="transport-to-shop-requested",
        target="transport-to-shop-picked-up",
        conditions=[has_transport_to_shop],
    )
    def transport_to_shop_picked_up(self):
        self.updated_at = timezone.now()

        if self.transport_to_shop.picked_up_at is None:
            self.transport_to_shop.picked_up_at = timezone.now()

        self.save()

    @transition(
        field=state,
        source="transport-to-shop-picked-up",
        target="transport-to-shop-delivered",
        conditions=[has_transport_to_shop],
    )
    def transport_to_shop_delivered(self):
        self.updated_at = timezone.now()

        if self.transport_to_shop.delivered_at is None:
            self.transport_to_shop.delivered_at = timezone.now()

        self.save()

    @transition(
        field=state,
        source="transport-to-shop-delivered",
        target="requires-review",
    )
    def receive_in_shop(self):
        self.updated_at = timezone.now()

    @transition(
        field=state,
        source="requires-review",
        target="rejected",
    )
    def reject_work(self):
        self.updated_at = timezone.now()

    @transition(
        field=state,
        source="requires-review",
        target=RETURN_VALUE("requires-approval", "ready-for-repair"),
        conditions=[has_review],
    )
    def mark_as_reviewed(self):
        self.updated_at = timezone.now()

        requested_services = [
            unit.service.service.slug for unit in self.current_order.order_units.all()
        ]
        suggested_services = [
            unit.service.service.slug for unit in self.reviewed_order.order_units.all()
        ]

        if set(requested_services) == set(suggested_services):
            return "ready-for-repair"

        self.send_mail("Your order has been altered")
        return "requires-approval"

    @transition(
        field=state,
        source="requires-approval",
        target=RETURN_VALUE(
            "needs-extra-payment",
            "ready-for-repair",
            "rejected",
        ),
    )
    def approve_review(self):
        self.updated_at = timezone.now()
        self.current_order = self.reviewed_order
        self.reviewed_order = None

        if self.amount_to_pay > 0:
            self.create_pending_payments()
            return "needs-extra-payment"

        return "ready-for-repair"

    @transition(
        field=state,
        source="requires-approval",
        target="rejected",
    )
    def reject_review(self):
        self.updated_at = timezone.now()
        return "rejected"

    @transition(
        field=state,
        source="ready-for-repair",
        target="repaired",
    )
    def repaired(self):
        self.updated_at = timezone.now()

    @transition(
        field=state,
        source=["rejected", "repaired"],
        target="transport-to-customer-requested",
        conditions=[has_transport_to_customer],
    )
    def transport_to_customer_requested(self):
        self.send_mail("Your device is on its way back!")
        self.updated_at = timezone.now()

    @transition(
        field=state,
        source="transport-to-customer-requested",
        target="transport-to-customer-picked-up",
        conditions=[has_transport_to_customer],
    )
    def transport_to_customer_picked_up(self):
        self.updated_at = timezone.now()

        if self.transport_to_customer.picked_up_at is None:
            self.transport_to_customer.picked_up_at = timezone.now()

    @transition(
        field=state,
        source="transport-to-customer-picked-up",
        target="transport-to-customer-delivered",
        conditions=[has_transport_to_customer],
    )
    def transport_to_customer_delivered(self):
        self.updated_at = timezone.now()

        if self.transport_to_customer.delivered_at is None:
            self.transport_to_customer.delivered_at = timezone.now()

    def __str__(self):
        return f"Order {self.pk}: {self.first_name} {self.last_name}"


class Payment(models.Model):
    """A payment assigned to an order. Can be either `pending` or `paid`."""

    order = models.ForeignKey(Order, related_name="payments", on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    currency = models.CharField(max_length=10, choices=(("SEK", " kr"),), default="SEK")

    status = models.CharField(
        max_length=10,
        choices=(
            ("pending", "Pending"),
            ("paid", "Paid"),
        ),
        default="pending",
    )

    payment_reference = models.TextField(blank=True)
    payment_meta = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


class OrderGroup(models.Model):
    """A group of order units belonging to an order."""

    CUSTOMER_ORDER = "order"
    SHOP_REVIEW = "shop-review"

    order = models.ForeignKey(
        Order, related_name="order_groups", on_delete=models.CASCADE
    )
    type = models.CharField(
        max_length=20,
        choices=(
            (CUSTOMER_ORDER, "Customer order"),
            (SHOP_REVIEW, "Shop review"),
        ),
        default=CUSTOMER_ORDER,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total(self):
        return sum([unit.service.price for unit in self.order_units.all()])

    def __str__(self):
        return f"Order group {self.pk}: {self.order}"


class OrderUnit(models.Model):
    """A single unit belonging to an order group."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"

    group = models.ForeignKey(
        OrderGroup, related_name="order_units", on_delete=models.CASCADE
    )
    service = models.ForeignKey(DeviceService, on_delete=models.CASCADE)

    accepted = models.BooleanField(
        default=True,
        help_text=(
            "If the customer has accepted the service or not. Defaults to "
            "accepted for all services that the customer initiated. All other "
            "services must be accepted by the customer before being charged."
        ),
    )
    required = models.BooleanField(
        default=False,
        help_text=(
            "If the service is required before proceeding with the order. This "
            "is typically set for services that the shop consider mandatory."
        ),
    )

    review_status = models.CharField(
        max_length=20,
        choices=(
            (PENDING, "Pending"),
            (CONFIRMED, "Confirmed"),
            (REJECTED, "Rejected"),
        ),
        default=PENDING,
    )

    added_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    repaired_at = models.DateTimeField(null=True, blank=True)


class OrderDeliverySlot(models.Model):
    order = models.OneToOneField(
        Order,
        related_name="slot",
        on_delete=models.CASCADE,
    )
    slot = models.ForeignKey(DeliverySlot, on_delete=models.CASCADE)

    date = models.DateField()

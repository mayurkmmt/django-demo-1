import datetime

from django.utils import timezone
from django_fsm_log.models import StateLog
from rest_framework import serializers

from ..devices.models import Device, DeviceService
from ..devices.serializers import DeviceSerializer, DeviceServiceSerializer
from ..services.models import Service
from .models import (
    Order,
    OrderDeliverySlot,
    OrderGroup,
    OrderUnit,
    Payment,
    PromotionalCode,
)


class OrderDeliverySlotSerializer(serializers.ModelSerializer):
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()

    def get_start(self, obj):
        start = datetime.datetime.combine(obj.date, obj.slot.slot_start)
        return timezone.make_aware(start)

    def get_end(self, obj):
        end = datetime.datetime.combine(obj.date, obj.slot.slot_end)
        return timezone.make_aware(end)

    class Meta:
        model = OrderDeliverySlot
        fields = [
            "slot",
            "date",
            "start",
            "end",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class OrderUnitSerializer(serializers.ModelSerializer):
    service = DeviceServiceSerializer(read_only=True)
    service_slug = serializers.SlugRelatedField(
        write_only=True,
        source="service",
        slug_field="slug",
        queryset=Service.objects.all(),
    )

    class Meta:
        model = OrderUnit
        fields = "__all__"


class OrderGroupSerializer(serializers.ModelSerializer):
    order_units = OrderUnitSerializer(many=True, read_only=True)
    total = serializers.ReadOnlyField()
    services = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
    )

    class Meta:
        model = OrderGroup
        exclude = ["order"]


class ReviewSerializer(serializers.ModelSerializer):
    services = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
    )

    # TODO: Add a list of mandatory services.

    class Meta:
        model = OrderGroup
        fields = ["order", "services"]

    def create(self, validated_data):
        services = validated_data.pop("services")
        order_group = validated_data["order"].order_groups.create()

        for service_slug in services:
            service = DeviceService.objects.get(
                service__slug=service_slug,
                device=validated_data["order"].device,
            )
            OrderUnit.objects.create(group=order_group, service=service)
        return order_group


class PromoCodeSerializer(serializers.ModelSerializer):
    activations = serializers.ReadOnlyField()

    class Meta:
        model = PromotionalCode
        fields = "__all__"


class OrderSerializer(serializers.ModelSerializer):
    services = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
    )
    device = DeviceSerializer(read_only=True)
    device_slug = serializers.SlugRelatedField(
        write_only=True,
        source="device",
        queryset=Device.objects.all(),
        slug_field="slug",
    )
    current_order = OrderGroupSerializer(read_only=True)
    reviewed_order = OrderGroupSerializer(read_only=True)

    amount_to_pay = serializers.ReadOnlyField()
    total_price = serializers.ReadOnlyField()

    payments = PaymentSerializer(many=True, read_only=True)

    order_id = serializers.CharField(read_only=True)

    slot = OrderDeliverySlotSerializer(
        required=True,
    )

    tracking_code = serializers.SerializerMethodField()

    states = serializers.SerializerMethodField()

    def get_tracking_code(self, obj):
        if obj.transport_to_shop is None:
            return ""
        return obj.transport_to_shop.tracking_code

    def get_states(self, obj):
        entries = StateLog.objects.for_(obj)
        return [
            {
                "source_state": entry.source_state,
                "state": entry.state,
                "timestamp": entry.timestamp,
            }
            for entry in entries
        ]

    class Meta:
        model = Order
        fields = "__all__"

    def create(self, validated_data):
        services = validated_data.pop("services")
        slot = validated_data.pop("slot")
        order = Order.objects.create(**validated_data)

        promo = validated_data["promo_code"]
        if promo:
            promo.activations = promo.activations + 1
            promo.save()
            if promo.discount_percent:
                order.discount_percent = promo.discount_percent
            if promo.discount_amount:
                order.discount_amount = promo.discount_amount

        OrderDeliverySlot.objects.create(order=order, **slot)

        order_group = order.order_groups.create()
        for service_slug in services:
            service = DeviceService.objects.get(
                service__slug=service_slug,
                device=order.device,
            )
            OrderUnit.objects.create(group=order_group, service=service)

        order.current_order = order_group
        order.save()

        order.register_payment_intent()
        order.save()

        return order

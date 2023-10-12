import json

import stripe
from django import http
from django.conf import settings
from django.utils import timezone
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Order, Payment, PromotionalCode
from .serializers import OrderSerializer, PromoCodeSerializer, ReviewSerializer


class IsPost(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.method == "POST"


class OrderStatusView(generic.DetailView):
    model = Order
    context_object_name = "order"
    template_name = "status.html"

    def get_object(self):
        return self.model.objects.get(code=self.kwargs["code"])


class PromoCodeViewSet(viewsets.ViewSet):
    lookup_field = "code"

    @action(
        detail=True,
        methods=["get"],
        url_path="verify",
    )
    def verify(self, request, code=None):
        data = None
        try:
            promo = PromotionalCode.objects.get(code=code)

            if promo.expiration < timezone.now():
                data = {"error": "Promotion expired."}
            if promo.max_activations > 0 and promo.activations > promo.max_activations:
                data = {"error": "Promotion not available."}
        except PromotionalCode.DoesNotExist:
            data = {"error": "Promotion not found."}

        if not data:
            data = PromoCodeSerializer(promo).data

        return Response(data, status=status.HTTP_200_OK)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated | IsPost]

    def get_queryset(self):
        queryset = Order.objects.all()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(shop__users=self.request.user)
        return queryset

    @action(detail=True, methods=["post"], url_path="mark-as-paid")
    def mark_as_paid(self, request, pk=None):
        order = self.get_object()

        for payment in order.payments.all():
            payment.status = "paid"
            payment.save()

        order.mark_as_paid()
        order.save()

        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        order = self.get_object()

        serializer = ReviewSerializer(
            data={**request.data, **{"order": order.pk}},
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_group = serializer.save()

        order.reviewed_order = order_group
        order.mark_as_reviewed()
        order.save()

        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    def received(self, request, pk=None):
        order = self.get_object()

        order.receive_in_shop()
        order.save()

        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"], url_path="mark-as-repaired")
    def mark_as_repaired(self, request, pk=None):
        order = self.get_object()

        for group in order.order_groups.all():
            for unit in group.order_units.all():
                unit.repaired_at = timezone.now()
                unit.save()

        order.repaired()
        order.save()

        return Response(self.get_serializer(order).data)

    @action(
        detail=False,
        methods=["get"],
        url_path=r"(?P<code>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",  # noqa
        permission_classes=[],
    )
    def by_code(self, request, code=None, pk=None):
        """Get a single order object identified by its code."""
        try:
            order = Order.objects.get(code=code)
            return Response(self.get_serializer(order).data)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(
        detail=False,
        methods=["post"],
        url_path=r"(?P<code>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/accept",  # noqa
    )
    def accept(self, request, code=None, pk=None):
        """Accept review of order identified by code."""
        try:
            order = Order.objects.get(code=code)
            order.approve_review()
            order.save()
            return Response(self.get_serializer(order).data)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(
        detail=False,
        methods=["post"],
        url_path=r"(?P<code>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/reject",  # noqa
    )
    def reject(self, request, code=None, pk=None):
        """Reject review of order identified by code."""
        try:
            order = Order.objects.get(code=code)
            order.reject_review()
            order.save()
            return Response(self.get_serializer(order).data)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )


@require_POST
@csrf_exempt
def webhook_handler(request):
    """Handle webhook calls from Stripe."""
    signature = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(
            request.body,
            signature,
            settings.STRIPE_ENDPOINT_SECRET,
        )
    except ValueError as e:
        print(e)
        return http.HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        print("Invalid signature", e)
        return http.HttpResponse(status=400)

    event_dict = event.to_dict()

    if (
        event_dict["type"] == "charge.succeeded"
        and event_dict["data"]["object"]["paid"]
    ):
        payment_id = event_dict["data"]["object"]["metadata"]["payment_id"]

        payment = Payment.objects.get(pk=payment_id)
        payment.status = "paid"
        payment.payment_meta = json.dumps(event_dict)
        payment.save()

        payment.order.mark_as_paid()
        payment.order.save()

    return http.HttpResponse(status=200)

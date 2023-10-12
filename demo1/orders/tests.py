from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from ..devices.models import Brand, Device, DeviceService, ProductFamily
from ..logistics.models import DeliveryArea, DeliveryService, DeliverySlot, Transport
from ..services.models import Service
from ..shops.models import Shop
from .models import Order, PromotionalCode


@override_settings(STRIPE_ENABLED=False, SEND_EMAILS=False)
class CreateOrderTest(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@admin.com",
            password="admin",
            is_superuser=True,
        )
        self.technician = User.objects.create_user(
            username="technician",
            email="technician@technician.com",
            password="technician",
        )
        service1 = Service.objects.create(
            slug="damaged-screen",
            name="Damaged screen",
        )
        service2 = Service.objects.create(
            slug="battery-replacement",
            name="Battery replacement",
        )
        service3 = Service.objects.create(
            slug="rear-camera-replacement",
            name="Rear camera replacement",
        )

        brand = Brand.objects.create(slug="apple", name="Apple")
        family = ProductFamily.objects.create(
            brand=brand,
            slug="iphone",
            name="iPhone",
        )
        device = Device.objects.create(
            product_family=family,
            slug="iphone-x",
            name="iPhone X",
        )

        DeviceService.objects.create(
            service=service1,
            device=device,
            price="10.00",
        )
        DeviceService.objects.create(
            service=service2,
            device=device,
            price="10.00",
        )
        DeviceService.objects.create(
            service=service3,
            device=device,
            price="10.00",
        )

        shop = Shop.objects.create(
            name="Shop 1",
        )
        shop.users.add(self.technician)
        delivery_service = DeliveryService.objects.create(name="Delivery service 1")
        Transport.objects.create(
            service=delivery_service,
            direction=Transport.CUSTOMER,
        )
        Transport.objects.create(
            service=delivery_service,
            direction=Transport.SHOP,
        )

        delivery_area = DeliveryArea.objects.create(
            service=delivery_service, name="Delivery area 1"
        )

        DeliverySlot.objects.create(
            area=delivery_area,
            postal_code_range_start="00000",
            slot_start="00:00",
            slot_end="23:59",
        )
        PromotionalCode.objects.create(code="TEST-10", discount_amount="10.00")

    def test_create_order(self):
        promo = PromotionalCode.objects.first()
        slot = DeliverySlot.objects.first()
        data = {
            "firstName": "Testar",
            "lastName": "Testar",
            "email": "testar@testar.com",
            "address": "Avenida del test 3",
            "city": "Marbella",
            "postalCode": "12312312",
            "preferredLanguage": "es",
            "country": "ES",
            "deviceSlug": "iphone-x",
            "slot": {
                "date": "2019-09-16",
                "slot": slot.pk,
            },
            "services": [
                "damaged-screen",
                "rear-camera-replacement",
            ],
            "promoCode": promo.pk,
        }
        url = reverse("api:order-list")

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["preferred_language"], "es")

    def test_mark_order_as_paid(self):
        self.client.force_authenticate(user=self.admin)
        self.test_create_order()
        order = Order.objects.first()

        data = {}
        url = reverse("api:order-mark-as-paid", args=[order.pk])

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.get(pk=order.pk).state, "paid")

    def test_get_order_by_code_valid(self):
        self.test_create_order()
        order = Order.objects.first()

        url = reverse("api:order-by-code", kwargs={"code": order.code})

        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, 200)

    def test_get_order_by_code_invalid(self):
        url = reverse(
            "api:order-by-code",
            kwargs={"code": "00000000-0000-0000-0000-000000000000"},
        )
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 404)

    def test_assign_to_shop(self):
        self.client.force_authenticate(user=self.technician)
        self.test_mark_order_as_paid()
        order = Order.objects.first()
        shop = Shop.objects.first()
        order.shop = shop
        order.assigned_to_shop()
        order.save()

    def test_deliver_to_shop(self):
        self.client.force_authenticate(user=self.technician)
        self.test_assign_to_shop()
        order = Order.objects.first()

        transport = Transport.objects.filter(direction=Transport.SHOP).first()
        order.transport_to_shop = transport
        order.transport_to_shop_requested()
        order.transport_to_shop_picked_up()
        order.transport_to_shop_delivered()
        order.save()

    def test_receive_in_shop(self):
        self.client.force_authenticate(user=self.technician)
        self.test_deliver_to_shop()
        order = Order.objects.first()

        data = {}
        url = reverse("api:order-received", args=[order.pk])

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Order.objects.get(pk=order.pk).state,
            "requires-review",
        )

    def test_create_order_review_unchanged(self):
        self.client.force_authenticate(user=self.technician)
        self.test_receive_in_shop()
        order = Order.objects.first()

        data = {
            "services": [
                "damaged-screen",
                "rear-camera-replacement",
            ],
        }
        url = reverse("api:order-review", args=[order.pk])

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Order.objects.get(pk=order.pk).state,
            "ready-for-repair",
        )

    def test_create_order_review_addition(self):
        self.client.force_authenticate(user=self.technician)
        self.test_receive_in_shop()
        order = Order.objects.first()

        data = {
            "services": [
                "damaged-screen",
                "rear-camera-replacement",
                "battery-replacement",
            ],
        }
        url = reverse("api:order-review", args=[order.pk])

        response = self.client.post(url, data, format="json")

        order = Order.objects.get(pk=order.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.state, "requires-approval")

    def test_create_order_review_subtraction(self):
        self.client.force_authenticate(user=self.technician)
        self.test_receive_in_shop()
        order = Order.objects.first()

        data = {
            "services": [
                "damaged-screen",
            ],
        }
        url = reverse("api:order-review", args=[order.pk])

        response = self.client.post(url, data, format="json")

        order = Order.objects.get(pk=order.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.state, "requires-approval")

    def test_create_order_review_alteration(self):
        self.client.force_authenticate(user=self.technician)
        self.test_receive_in_shop()
        order = Order.objects.first()

        data = {
            "services": [
                "damaged-screen",
                "battery-replacement",
            ],
        }
        url = reverse("api:order-review", args=[order.pk])

        response = self.client.post(url, data, format="json")

        order = Order.objects.get(pk=order.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.state, "requires-approval")

    def test_approve_order_review_addition(self):
        self.test_create_order_review_addition()
        order = Order.objects.first()

        data = {}
        url = reverse("api:order-accept", args=[order.code])

        response = self.client.post(url, data, format="json")

        order = Order.objects.get(pk=order.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.state, "needs-extra-payment")

    def test_reject_order_review_addition(self):
        self.test_create_order_review_addition()
        order = Order.objects.first()

        data = {}
        url = reverse("api:order-reject", args=[order.code])

        response = self.client.post(url, data, format="json")

        order = Order.objects.get(pk=order.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.state, "rejected")

    def test_pay_extras(self):
        self.test_approve_order_review_addition()
        order = Order.objects.first()

        data = {}
        url = reverse("api:order-mark-as-paid", args=[order.pk])

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Order.objects.get(pk=order.pk).state, "ready-for-repair"
        )  # noqa

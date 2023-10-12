from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token

from .devices.views import BrandViewSet
from .logistics.views import DeliverySlotView, PickupSlotView
from .orders.views import OrderViewSet, PromoCodeViewSet, webhook_handler
from .views import (
    CovidView,
    HomeView,
    MessageSentView,
    PPView,
    RMSView,
    ServiceDetailView,
    TosView,
    UserViewSet,
    V2ContactView,
    V2demo1ForBusinessView,
    V2FaqView,
    V2HowItWorksView,
    V2ServicesView,
    V2View,
    WarrantyView,
    WebflowTest,
    WidgetView,
)

router = routers.DefaultRouter()
router.register("orders", OrderViewSet)
router.register("promos", PromoCodeViewSet, basename="promo")
router.register("brands", BrandViewSet)
router.register("slots", DeliverySlotView)
router.register("users", UserViewSet, basename="user")

schema_view = get_schema_view(
    openapi.Info(
        title="demo1 API",
        default_version="v1",
        description="demo1 API documentation",
        contact=openapi.Contact(email="support@demo1.es"),
    ),
    public=True,
)

urlpatterns = (
    [
        path("api/", include((router.urls, "api"), namespace="api")),
        path("api/obtain-token/", obtain_auth_token),
        path("ckeditor/", include("ckeditor_uploader.urls")),
        path("i18n/", include("django.conf.urls.i18n")),
        path("stripe/webhook/", webhook_handler),
        path("accounts/", include("django.contrib.auth.urls")),
        re_path(
            r"^swagger(?P<format>\.json|\.yaml)$",
            schema_view.without_ui(cache_timeout=0),
            name="schema-json",
        ),
        path(
            "swagger/",
            schema_view.with_ui("swagger", cache_timeout=0),
            name="schema-swagger-ui",
        ),
        path(
            "docs/",
            schema_view.with_ui("redoc", cache_timeout=0),
            name="schema-redoc",
        ),
        re_path(
            "rms(.*)/",
            RMSView.as_view(),
            name="rms",
        ),
        path("admin/", admin.site.urls),
        path("api/pickupslot/", PickupSlotView.as_view()),
    ]
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    + static("assets/", document_root="assets/")
)

urlpatterns += i18n_patterns(
    path("", V2View.as_view(), name="home"),
    path("how-it-works", V2HowItWorksView.as_view(), name="how-it-works"),
    path("services", V2ServicesView.as_view(), name="services"),
    path(
        "demo1-for-business",
        V2demo1ForBusinessView.as_view(),
        name="demo1-for-business",
    ),
    path("contact", V2ContactView.as_view(), name="contact"),
    path("faqs", V2FaqView.as_view(), name="faqs"),
    path("tos/", TosView.as_view(), name="tos"),
    path("privacy/", PPView.as_view(), name="pp"),
    path("covid-19/", CovidView.as_view(), name="covid_19"),
    path("warranty/", WarrantyView.as_view(), name="warranty"),
    path("webflow-test/", WebflowTest.as_view(), name="webflow-test"),
    path("repair/", WidgetView.as_view(), name="repair"),
    path("repair/<slug:brand>/", WidgetView.as_view(), name="repair"),
    path("services/<slug:slug>/", ServiceDetailView.as_view(), name="service_detail"),
    path("status/<slug:code>/", WidgetView.as_view(), name="status"),
)

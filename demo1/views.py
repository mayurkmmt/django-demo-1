from django.conf import settings
from django.urls import reverse
from django.views.generic import DetailView, TemplateView
from django.views.generic.edit import FormView
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .content.models import FAQEntry
from .forms import ContactForm
from .serializers import UserSerializer
from .services.models import Service


class UserViewSet(viewsets.ViewSet):
    @action(detail=False, url_path="current", methods=["get"])
    def current_user(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class TosView(TemplateView):
    template_name = "tos.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["with_banner"] = settings.SHOW_BANNER
        return context


class PPView(TemplateView):
    template_name = "pp.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["with_banner"] = settings.SHOW_BANNER
        return context


class CovidView(TemplateView):
    template_name = "covid.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["with_banner"] = settings.SHOW_BANNER
        return context


class WarrantyView(TemplateView):
    template_name = "warranty.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["with_banner"] = settings.SHOW_BANNER
        return context


class WebflowTest(TemplateView):
    template_name = "webflow-test.html"


class WidgetView(TemplateView):
    template_name = "widget.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["api_url"] = settings.API_URL
        context["postal_code"] = self.request.GET.get("postal_code", "")
        context["stripe_key"] = settings.STRIPE_PUBLIC_KEY
        context["shipment_fee"] = settings.SHIPMENT_FEE
        return context


class RMSView(WidgetView):
    template_name = "rms.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["api_url"] = settings.API_URL
        return context


class HomeView(FormView):
    template_name = "home.html"
    form_class = ContactForm

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["faq_entries"] = FAQEntry.objects.all()
        context["with_banner"] = settings.SHOW_BANNER
        return context

    def get_success_url(self):
        return reverse("message_sent")

    def form_valid(self, form):
        form.send()
        return super().form_valid(form)


class ContactView(FormView):
    template_name = "contact.html"
    form_class = ContactForm

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["with_banner"] = settings.SHOW_BANNER
        return context

    def get_success_url(self):
        return reverse("message_sent")

    def form_valid(self, form):
        form.send()
        return super().form_valid(form)


class MessageSentView(TemplateView):
    template_name = "message_sent.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["with_banner"] = settings.SHOW_BANNER
        return context


class ServiceDetailView(DetailView):
    template_name = "service-detail.html"
    model = Service

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["with_banner"] = settings.SHOW_BANNER
        print(context)
        return context


# V2 Site
class V2View(WidgetView):
    template_name = "v2/home.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["faq_entries"] = FAQEntry.objects.all()
        context["with_banner"] = settings.SHOW_BANNER
        context["api_url"] = settings.API_URL
        context["postal_code"] = self.request.GET.get("postal_code", "")
        context["stripe_key"] = settings.STRIPE_PUBLIC_KEY
        context["shipment_fee"] = settings.SHIPMENT_FEE
        return context


class V2HowItWorksView(WidgetView):
    template_name = "v2/how-it-works.html"


class V2ServicesView(WidgetView):
    template_name = "v2/services.html"


class V2ContactView(WidgetView):
    template_name = "v2/contact.html"


class V2demo1ForBusinessView(WidgetView):
    template_name = "v2/demo1-for-business.html"


class V2FaqView(WidgetView):
    template_name = "v2/faqs.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["faq_entries"] = FAQEntry.objects.all()
        return context

from django.apps import AppConfig


class ServicesConfig(AppConfig):
    name = "demo1.services"

    def ready(self):
        import demo1.services.signals  # noqa

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ServiceAppConfig(AppConfig):
    name = "tests.service_app"
    label = "service_app"
    verbose_name = _("Translation test")

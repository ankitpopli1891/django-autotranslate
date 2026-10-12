import typing as t

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _

from .services import TranslatorService

SERVICE_SETTING = "AUTOTRANSLATE_SERVICE"
DEFAULT_SERVICE = "autotranslate.services.GoogleTranslatorService"


def get_service_config() -> tuple[str, dict[str, t.Any]]:
    """
    Get the configured translation service from ``settings.AUTOTRANSLATE_SERVICE``.

    The setting may be the import path of a service class, or a dictionary with
    the import path as ``BACKEND`` and an optional ``OPTIONS`` dictionary of keyword
    arguments for the service's constructor.

    :raises ~django.core.exceptions.ImproperlyConfigured: If the setting is not in one of these forms.
    :return: A tuple of the service's import path and its options.
    """
    config = getattr(settings, SERVICE_SETTING, DEFAULT_SERVICE)
    if isinstance(config, str):
        return config, {}
    if (
        isinstance(config, dict)
        and isinstance(config.get("BACKEND"), str)
        and isinstance(config.get("OPTIONS", {}), dict)
    ):
        return config["BACKEND"], dict(config.get("OPTIONS", {}))
    raise ImproperlyConfigured(
        _(
            "{setting} must be an import path or a dictionary with a BACKEND import "
            "path and an optional OPTIONS dictionary."
        ).format(setting=f"settings.{SERVICE_SETTING}")
    )


def get_service_import_path() -> str:
    """
    Get the import path of the configured translation service.
    """
    return get_service_config()[0]


def get_translator(
    service_path: str | None = None, source: str | None = None
) -> TranslatorService:
    """
    Returns an instantiated service of the configured translator or the translator at
    the given path.

    The ``OPTIONS`` in ``settings.AUTOTRANSLATE_SERVICE`` are only used if the
    service is the configured service.

    :param service_path: The path to the translator service to use if different from
        settings.AUTOTRANSLATE_SERVICE.
    :param source: Where the given service path came from, used in error messages.
    :raises ~django.core.exceptions.ImproperlyConfigured: If the service path is not a valid translator
        service, does not subclass TranslatorService or its options are invalid.
    :return: An instantiated translator service.
    """
    backend, options = get_service_config()
    if service_path is None or service_path == backend:
        service_path = backend
        source = f"settings.{SERVICE_SETTING}"
    else:
        options = {}

    try:
        translator = import_string(service_path)
    except ImportError as ie:
        message = (
            _("Could not import the translation service {service} ({source}).")
            if source
            else _("Could not import the translation service {service}.")
        )
        raise ImproperlyConfigured(
            message.format(service=service_path, source=source)
        ) from ie
    if not (isinstance(translator, type) and issubclass(translator, TranslatorService)):
        message = (
            _(
                "The translation service {service} ({source}) is not a subclass of "
                "{base}."
            )
            if source
            else _("The translation service {service} is not a subclass of {base}.")
        )
        raise ImproperlyConfigured(
            message.format(
                service=service_path,
                source=source,
                base="autotranslate.services.TranslatorService",
            )
        )
    try:
        return translator(**options)
    except TypeError as err:
        raise ImproperlyConfigured(
            _("Invalid options for the translation service {service}: {error}").format(
                service=service_path, error=err
            )
        ) from err


def language_codes() -> dict[str, str]:
    """
    Get a mapping of language codes to their names from Django settings.
    """
    return {code: name for code, name in getattr(settings, "LANGUAGES", {})}

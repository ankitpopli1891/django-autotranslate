import shutil
import tempfile
from pathlib import Path
from unittest import mock

import polib
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import TestCase, override_settings

from autotranslate.config import (
    DEFAULT_SERVICE,
    get_service_config,
    get_service_import_path,
    get_translator,
)
from autotranslate.services import (
    AmazonTranslateTranslatorService,
    GoogleAPITranslatorService,
    GoogleTranslatorService,
    TranslatorService,
)

DATA_DIR = Path(__file__).parent / "data"


class ConfigurableService(TranslatorService):
    def __init__(self, *, prefix="[default]"):
        self.prefix = prefix

    def translate_strings(self, strings, target_language, source_language="en"):
        return (f"{self.prefix} {string}" for string in strings)


SERVICE = f"{__name__}.ConfigurableService"


class ServiceSettingTestCase(TestCase):
    def test_default(self):
        self.assertEqual((DEFAULT_SERVICE, {}), get_service_config())
        self.assertIsInstance(get_translator(), GoogleTranslatorService)

    @override_settings(AUTOTRANSLATE_SERVICE=SERVICE)
    def test_import_path(self):
        self.assertEqual((SERVICE, {}), get_service_config())
        self.assertEqual(SERVICE, get_service_import_path())
        self.assertEqual("[default]", get_translator().prefix)

    @override_settings(
        AUTOTRANSLATE_SERVICE={"BACKEND": SERVICE, "OPTIONS": {"prefix": "[x]"}}
    )
    def test_backend_and_options(self):
        self.assertEqual((SERVICE, {"prefix": "[x]"}), get_service_config())
        self.assertEqual(SERVICE, get_service_import_path())
        self.assertEqual("[x]", get_translator().prefix)
        # options apply when the configured service is given explicitly
        self.assertEqual("[x]", get_translator(SERVICE).prefix)

    @override_settings(AUTOTRANSLATE_SERVICE={"BACKEND": SERVICE})
    def test_options_optional(self):
        self.assertEqual("[default]", get_translator().prefix)

    @override_settings(
        AUTOTRANSLATE_SERVICE={
            "BACKEND": "autotranslate.services.GoogleTranslatorService",
            "OPTIONS": {"retries": 7},
        }
    )
    def test_options_only_for_configured_backend(self):
        # a different service does not get the configured service's options
        self.assertEqual("[default]", get_translator(SERVICE).prefix)

    def test_invalid_setting(self):
        for setting in [
            {"OPTIONS": {}},
            {"BACKEND": SERVICE, "OPTIONS": ["prefix"]},
            ["autotranslate.services.GoogleTranslatorService"],
        ]:
            with (
                self.subTest(setting=setting),
                override_settings(AUTOTRANSLATE_SERVICE=setting),
            ):
                with self.assertRaisesMessage(
                    ImproperlyConfigured, "settings.AUTOTRANSLATE_SERVICE must be"
                ):
                    get_service_config()

    @override_settings(
        AUTOTRANSLATE_SERVICE={"BACKEND": SERVICE, "OPTIONS": {"bogus": 1}}
    )
    def test_invalid_options(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "bogus"):
            get_translator()

    def test_error_names_source(self):
        with override_settings(AUTOTRANSLATE_SERVICE="no.such.Service"):
            with self.assertRaisesMessage(
                ImproperlyConfigured, "(settings.AUTOTRANSLATE_SERVICE)"
            ):
                get_translator()
        with self.assertRaisesMessage(ImproperlyConfigured, "(--service)"):
            get_translator("no.such.Service", source="--service")
        with self.assertRaisesMessage(
            ImproperlyConfigured, "autotranslate.config.language_codes"
        ):
            get_translator("autotranslate.config.language_codes", source="--service")


class CommandOptionsTestCase(TestCase):
    """
    The default --service is read from settings when the command module is imported,
    so these tests name the service explicitly - options apply because it is the
    configured service.
    """

    def setUp(self):
        self.locale_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.locale_dir)
        messages = self.locale_dir / "de" / "LC_MESSAGES"
        messages.mkdir(parents=True)
        shutil.copy(DATA_DIR / "django.po", messages / "django.po")

    def translate(self):
        call_command(
            "autotranslate", "--path", str(self.locale_dir), "--service", SERVICE
        )
        return polib.pofile(str(self.locale_dir / "de" / "LC_MESSAGES" / "django.po"))

    @override_settings(
        AUTOTRANSLATE_SERVICE={"BACKEND": SERVICE, "OPTIONS": {"prefix": "[opt]"}}
    )
    def test_command_uses_configured_options(self):
        self.assertEqual("[opt] Location", self.translate()[0].msgstr)

    def test_command_service_without_options(self):
        self.assertEqual("[default] Location", self.translate()[0].msgstr)

    def test_bad_service_error_names_option(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "(--service)"):
            call_command(
                "autotranslate",
                "--path",
                str(self.locale_dir),
                "--service",
                "no.such.Service",
            )


class GoogleOptionsTestCase(TestCase):
    def test_defaults(self):
        service = GoogleTranslatorService()
        self.assertEqual(GoogleTranslatorService.retries, service.retries)
        self.assertEqual("zh-cn", service.service_language("zh-hans"))

    def test_options(self):
        service = GoogleTranslatorService(
            retries=5,
            retry_delay=0.5,
            rate_limit_delay=10,
            language_map={"sr-latn": "sr", "zh-hans": "zh"},
        )
        self.assertEqual(5, service.retries)
        self.assertEqual(0.5, service.retry_delay)
        self.assertEqual(10, service.rate_limit_delay)
        self.assertEqual("sr", service.service_language("sr-latn"))
        self.assertEqual("zh", service.service_language("zh-hans"))
        # defaults that were not overridden remain
        self.assertEqual("zh-tw", service.service_language("zh-hant"))
        # the class defaults are not modified
        self.assertIsNone(GoogleTranslatorService().service_language("sr-latn"))


class GoogleAPIOptionsTestCase(TestCase):
    def test_api_key_required(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "api_key"):
            GoogleAPITranslatorService()

    @override_settings(
        AUTOTRANSLATE_SERVICE={
            "BACKEND": "autotranslate.services.GoogleAPITranslatorService",
            "OPTIONS": {"api_key": "secret", "max_segments": 2},
        }
    )
    def test_options(self):
        with mock.patch("googleapiclient.discovery.build") as build:
            api = build.return_value.translations.return_value.list
            api.return_value.execute.side_effect = lambda: {
                "translations": [
                    {"translatedText": f"[de] {q}"} for q in api.call_args.kwargs["q"]
                ]
            }
            service = get_translator()
            translated = list(service.translate_strings(["a", "b", "c"], "de"))

        build.assert_called_once_with("translate", "v2", developerKey="secret")
        self.assertEqual(["[de] a", "[de] b", "[de] c"], translated)
        # max_segments limits the strings in each request
        self.assertEqual(
            [["a", "b"], ["c"]], [call.kwargs["q"] for call in api.call_args_list]
        )


class AmazonOptionsTestCase(TestCase):
    @override_settings(
        AUTOTRANSLATE_SERVICE={
            "BACKEND": "autotranslate.services.AmazonTranslateTranslatorService",
            "OPTIONS": {"region_name": "us-west-2", "aws_access_key_id": "key"},
        }
    )
    def test_client_options(self):
        with mock.patch("boto3.client") as client:
            service = get_translator()
        client.assert_called_once_with(
            "translate", region_name="us-west-2", aws_access_key_id="key"
        )
        self.assertIs(client.return_value, service.service)

    def test_no_options(self):
        with mock.patch("boto3.client") as client:
            AmazonTranslateTranslatorService()
        client.assert_called_once_with("translate")

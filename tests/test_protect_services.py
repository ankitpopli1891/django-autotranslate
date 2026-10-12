import re
from unittest import mock

from django.test import TestCase

from autotranslate.protect.guards import HTMLGuard, TokenGuard
from autotranslate.services import (
    AmazonTranslateTranslatorService,
    GoogleAPITranslatorService,
    GoogleTranslatorService,
    TranslatorService,
)


class ServiceGuardTestCase(TestCase):
    def test_guards(self):
        self.assertIsInstance(TranslatorService.guard, TokenGuard)
        self.assertIsInstance(GoogleTranslatorService.guard, TokenGuard)
        self.assertIsInstance(GoogleAPITranslatorService.guard, HTMLGuard)
        self.assertIsInstance(AmazonTranslateTranslatorService.guard, HTMLGuard)

    def test_protect_and_restore(self):
        service = TranslatorService()
        protected = service.protect("Saved %s", ["python-format"])
        self.assertEqual("Saved __x0__", protected.encoded)
        self.assertEqual(
            "Gespeichert %s", service.restore(protected, "Gespeichert __x0__")
        )
        self.assertIsNone(service.restore(protected, "Gespeichert"))

    def test_google_api_sends_html(self):
        with mock.patch("googleapiclient.discovery.build") as build:
            service = GoogleAPITranslatorService(api_key="secret")
        api = build.return_value.translations.return_value.list
        api.return_value.execute.return_value = {
            "translations": [{"translatedText": "x"}]
        }
        list(service.translate_strings(["a"], "de"))
        service.translate_string("a", "de")
        self.assertEqual(
            ["html", "html"], [c.kwargs["format"] for c in api.call_args_list]
        )

    def test_old_api_removed(self):
        import autotranslate.services as services

        for name in ["PLACEHOLDER", "placeholders", "TEXT"]:
            self.assertFalse(hasattr(services, name), name)
        for name in [
            "humanize_placeholders",
            "restore_placeholders",
            "validate_translation",
            "fix_translation",
        ]:
            self.assertFalse(hasattr(TranslatorService, name), name)

    def test_google_api_round_trip(self):
        with mock.patch("googleapiclient.discovery.build") as build:
            service = GoogleAPITranslatorService(api_key="secret")
        api = build.return_value.translations.return_value.list
        source = 'Read <a href="%(url)s">docs</a>, %(name)s'
        protected = service.protect(source, ["python-format"])
        translated = protected.encoded.replace("Read", "Lesen Sie").replace(
            "docs", "Doku"
        )
        api.return_value.execute.return_value = {
            "translations": [{"translatedText": translated}]
        }
        self.assertEqual(
            [translated], list(service.translate_strings([protected.encoded], "de"))
        )
        self.assertEqual([protected.encoded], api.call_args.kwargs["q"])
        self.assertNotEqual(source, protected.encoded)
        self.assertEqual(
            'Lesen Sie <a href="%(url)s">Doku</a>, %(name)s',
            service.restore(protected, translated),
        )
        # dropping the placeholder span from the response is rejected
        dropped = re.sub(r"<span[^>]*>[^<]*</span>", "", translated)
        self.assertNotEqual(translated, dropped)
        self.assertIsNone(service.restore(protected, dropped))

    def test_custom_html_guard(self):
        class HTMLService(TranslatorService):
            guard = HTMLGuard()

        protected = HTMLService().protect("Saved %s", ["python-format"])
        self.assertNotEqual("Saved __item__", protected.encoded)
        self.assertIn("<span", protected.encoded)
        self.assertIn("%s", protected.encoded)

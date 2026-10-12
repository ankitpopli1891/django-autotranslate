import shutil
import tempfile
from pathlib import Path
from unittest import mock

import polib
from django.core.management import call_command
from django.test import TestCase

from autotranslate.services import (
    AmazonTranslateTranslatorService,
    GoogleAPITranslatorService,
    GoogleTranslatorService,
    TranslatorService,
)

DATA_DIR = Path(__file__).parent / "data"


class ListedService(TranslatorService):
    """A service with a known list of supported languages."""

    languages = ["de", "es", "fr-CA", "pt", "pt-PT", "sr", "zh-CN", "zh-TW"]
    default_language_map = {"zh-hans": "zh-CN", "zh-hant": "zh-TW"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.list_calls = 0

    def supported_languages(self):
        self.list_calls += 1
        return self.languages

    def translate_strings(self, strings, target_language, source_language="en"):
        return (f"[{target_language}] {string}" for string in strings)


class LanguageResolutionTestCase(TestCase):
    def test_exact_match_uses_service_casing(self):
        service = ListedService()
        self.assertEqual("de", service.service_language("de"))
        self.assertEqual("pt-PT", service.service_language("pt-pt"))
        self.assertEqual("fr-CA", service.service_language("fr-ca"))

    def test_region_dropped(self):
        service = ListedService()
        self.assertEqual("pt", service.service_language("pt-br"))
        self.assertEqual("es", service.service_language("es-ar"))
        # no plain "fr" is supported
        self.assertIsNone(service.service_language("fr-be"))

    def test_script_not_dropped(self):
        # sr-latn -> sr would produce Cyrillic
        self.assertIsNone(ListedService().service_language("sr-latn"))

    def test_unsupported(self):
        self.assertIsNone(ListedService().service_language("ia"))

    def test_language_map(self):
        service = ListedService()
        self.assertEqual("zh-CN", service.service_language("zh-hans"))
        self.assertEqual("zh-TW", service.service_language("zh-hant"))

    def test_language_map_option(self):
        service = ListedService(
            language_map={"sr-latn": "sr", "pt-br": None, "zh-hans": "zh"}
        )
        self.assertEqual("sr", service.service_language("sr-latn"))
        self.assertIsNone(service.service_language("pt-br"))
        self.assertEqual("zh", service.service_language("zh-hans"))
        # defaults that were not overridden remain
        self.assertEqual("zh-TW", service.service_language("zh-hant"))
        # the class defaults are not modified
        self.assertEqual("zh-CN", ListedService().service_language("zh-hans"))

    def test_case_insensitive(self):
        service = ListedService(language_map={"ZH-Hans": "zh"})
        self.assertEqual("zh", service.service_language("zh-HANS"))
        self.assertEqual("pt", service.service_language("PT-BR"))

    def test_supported_languages_fetched_once(self):
        service = ListedService()
        for language in ["de", "pt-br", "ia", "es"]:
            service.service_language(language)
        self.assertEqual(1, service.list_calls)

    def test_unknown_supported_languages(self):
        class UnlistedService(TranslatorService):
            pass

        service = UnlistedService()
        self.assertEqual("pt-br", service.service_language("pt-BR"))
        self.assertEqual("ia", service.service_language("ia"))

    def test_subclass_without_super_init(self):
        class NoInit(ListedService):
            def __init__(self):
                self.list_calls = 0

        self.assertEqual("zh-CN", NoInit().service_language("zh-hans"))


class ServiceLanguageListTestCase(TestCase):
    def test_free_google(self):
        service = GoogleTranslatorService()
        self.assertEqual("zh-cn", service.service_language("zh-hans"))
        self.assertEqual("pt", service.service_language("pt-br"))
        self.assertEqual("no", service.service_language("nb"))
        self.assertIsNone(service.service_language("sr-latn"))
        self.assertIsNone(service.service_language("ia"))

    def test_google_api(self):
        with mock.patch("googleapiclient.discovery.build") as build:
            service = GoogleAPITranslatorService(api_key="secret")
        languages = build.return_value.languages.return_value.list
        languages.return_value.execute.return_value = {
            "languages": [
                {"language": code}
                for code in ["de", "iw", "no", "pt", "pt-PT", "sr", "zh-CN", "zh-TW"]
            ]
        }
        self.assertEqual("de", service.service_language("de"))
        self.assertEqual("zh-CN", service.service_language("zh-hans"))
        self.assertEqual("zh-TW", service.service_language("zh-hant"))
        self.assertEqual("pt", service.service_language("pt-br"))
        # Django's pt is European Portuguese, Google's pt is Brazilian
        self.assertEqual("pt-PT", service.service_language("pt"))
        self.assertEqual("no", service.service_language("nb"))
        self.assertIsNone(service.service_language("sr-latn"))
        self.assertIsNone(service.service_language("ia"))
        languages.assert_called_once_with()

    def test_amazon(self):
        with mock.patch("boto3.client") as client:
            service = AmazonTranslateTranslatorService(language_map={"he": "iw"})
        client.return_value.list_languages.side_effect = [
            {
                "Languages": [{"LanguageCode": c} for c in ["de", "es", "es-MX"]],
                "NextToken": "page2",
            },
            {
                "Languages": [
                    {"LanguageCode": c} for c in ["no", "pt", "sr", "zh", "zh-TW"]
                ]
            },
        ]
        self.assertEqual("es-MX", service.service_language("es-mx"))
        # Amazon's es is European Spanish, Latin American variants use es-MX
        for language in ["es-ar", "es-co", "es-ni", "es-ve"]:
            self.assertEqual("es-MX", service.service_language(language))
        self.assertEqual("es", service.service_language("es"))
        self.assertEqual("pt", service.service_language("pt-br"))
        self.assertEqual("pt-PT", service.service_language("pt"))
        self.assertEqual("zh", service.service_language("zh-hans"))
        self.assertEqual("zh-TW", service.service_language("zh-hant"))
        self.assertEqual("no", service.service_language("nb"))
        self.assertEqual("iw", service.service_language("he"))
        # Amazon's Serbian is Latin script
        self.assertEqual("sr", service.service_language("sr-latn"))
        self.assertIsNone(service.service_language("sr"))
        self.assertIsNone(service.service_language("ia"))
        # both pages were requested, once
        self.assertEqual(
            [mock.call(), mock.call(NextToken="page2")],
            client.return_value.list_languages.call_args_list,
        )
        # language_map is not passed to boto3
        client.assert_called_once_with("translate")


class CommandLanguageTestCase(TestCase):
    def test_unsupported_languages_skipped(self):
        locale_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, locale_dir)
        for locale in ["pt_BR", "sr_Latn", "zh_Hans", "ia"]:
            messages = locale_dir / locale / "LC_MESSAGES"
            messages.mkdir(parents=True)
            shutil.copy(DATA_DIR / "django.po", messages / "django.po")

        call_command(
            "autotranslate",
            "--path",
            str(locale_dir),
            "--service",
            f"{__name__}.ListedService",
        )

        def location(locale):
            po = polib.pofile(str(locale_dir / locale / "LC_MESSAGES" / "django.po"))
            return po[0].msgstr

        self.assertEqual("[pt] Location", location("pt_BR"))
        self.assertEqual("[zh-CN] Location", location("zh_Hans"))
        self.assertEqual("", location("sr_Latn"))
        self.assertEqual("", location("ia"))

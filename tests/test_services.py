import asyncio
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import polib
from django.core.management import call_command
from django.test import TestCase

from autotranslate.services import GoogleTranslatorService

DATA_DIR = Path(__file__).parent / "data"


class FakeGoogletransTranslator:
    """
    Stands in for googletrans.Translator. Like the real client, it breaks if it is
    used from more than one event loop or after it has been closed.
    """

    instances: list["FakeGoogletransTranslator"] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.loop = None
        self.closed = False
        self.calls = 0
        self.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.closed = True

    async def translate(self, text, dest, src):
        loop = asyncio.get_running_loop()
        if self.loop is None:
            self.loop = loop
        if self.loop is not loop or self.closed:
            raise RuntimeError("Event loop is closed")
        self.calls += 1

        def result(string):
            return SimpleNamespace(text=f"[{dest}] {string}")

        if isinstance(text, list):
            return [result(string) for string in text]
        return result(text)


class GoogleTranslatorServiceTestCase(TestCase):
    def setUp(self):
        FakeGoogletransTranslator.instances = []
        patcher = mock.patch("googletrans.Translator", FakeGoogletransTranslator)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_reuses_client_in_with_block(self):
        with GoogleTranslatorService() as service:
            self.assertEqual("[de] City", service.translate_string("City", "de"))
            self.assertEqual(
                ["[es] City", "[es] Cities"],
                list(service.translate_strings(["City", "Cities"], "es")),
            )
            self.assertEqual(
                ["[fr] Location"], list(service.translate_strings(["Location"], "fr"))
            )

        self.assertEqual(1, len(FakeGoogletransTranslator.instances))
        translator = FakeGoogletransTranslator.instances[0]
        self.assertEqual(3, translator.calls)
        self.assertTrue(translator.closed)

    def test_repeated_calls_outside_with_block(self):
        service = GoogleTranslatorService()
        self.assertEqual("[de] City", service.translate_string("City", "de"))
        self.assertEqual(
            ["[es] City", "[es] Cities"],
            list(service.translate_strings(["City", "Cities"], "es")),
        )

        self.assertEqual(2, len(FakeGoogletransTranslator.instances))
        self.assertTrue(all(tr.closed for tr in FakeGoogletransTranslator.instances))

    def test_service_reusable_after_with_block(self):
        service = GoogleTranslatorService()
        with service:
            service.translate_string("City", "de")
        self.assertEqual("[es] City", service.translate_string("City", "es"))
        with service:
            self.assertEqual("[fr] City", service.translate_string("City", "fr"))
        self.assertEqual(3, len(FakeGoogletransTranslator.instances))

    def test_command_uses_one_client_for_all_files(self):
        locale_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, locale_dir)
        for lang in ["de", "es", "fr"]:
            messages = locale_dir / lang / "LC_MESSAGES"
            messages.mkdir(parents=True)
            shutil.copy(DATA_DIR / "django.po", messages / "django.po")

        call_command(
            "autotranslate",
            "--path",
            str(locale_dir),
            "--service",
            "autotranslate.services.GoogleTranslatorService",
        )

        for lang in ["de", "es", "fr"]:
            po = polib.pofile(str(locale_dir / lang / "LC_MESSAGES" / "django.po"))
            self.assertEqual(f"[{lang}] Location", po[0].msgstr)
            self.assertEqual(f"[{lang}] City", po[1].msgstr_plural[0])

        self.assertEqual(1, len(FakeGoogletransTranslator.instances))
        self.assertEqual(3, FakeGoogletransTranslator.instances[0].calls)
        self.assertTrue(FakeGoogletransTranslator.instances[0].closed)


class GoogleRetryTestCase(TestCase):
    def setUp(self):
        import httpx

        FakeGoogletransTranslator.instances = []
        self.failures = 0

        test = self

        self.error = httpx.RemoteProtocolError("Server disconnected")

        class FlakyTranslator(FakeGoogletransTranslator):
            async def translate(self, text, dest, src):
                if test.failures:
                    test.failures -= 1
                    raise test.error
                return await super().translate(text, dest, src)

        for patcher in [
            mock.patch("googletrans.Translator", FlakyTranslator),
            mock.patch.object(GoogleTranslatorService, "retry_delay", 0),
            mock.patch.object(GoogleTranslatorService, "rate_limit_delay", 0),
        ]:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_retries_with_fresh_client(self):
        self.failures = 2
        with GoogleTranslatorService() as service:
            self.assertEqual("[de] City", service.translate_string("City", "de"))
        # the original client plus one fresh client per retry
        self.assertEqual(3, len(FakeGoogletransTranslator.instances))
        self.assertTrue(all(tr.closed for tr in FakeGoogletransTranslator.instances))

    def test_retries_outside_with_block(self):
        self.failures = 1
        self.assertEqual(
            "[de] City", GoogleTranslatorService().translate_string("City", "de")
        )

    def test_gives_up_after_retries(self):
        import httpx

        self.failures = GoogleTranslatorService.retries + 1
        with self.assertRaises(httpx.RemoteProtocolError):
            with GoogleTranslatorService() as service:
                service.translate_string("City", "de")

    def test_retries_rejected_requests(self):
        # googletrans raises this when Google responds with e.g. a 429
        self.error = Exception(
            "Unexpected status code \"429\" from ['translate.googleapis.com']"
        )
        self.failures = 2
        with GoogleTranslatorService() as service:
            self.assertEqual("[de] City", service.translate_string("City", "de"))

    def test_rejected_requests_raise_after_retries(self):
        from autotranslate.services import ServiceUnavailable

        self.error = Exception('Unexpected status code "429" from []')
        self.failures = GoogleTranslatorService.retries + 1
        with self.assertRaises(ServiceUnavailable):
            with GoogleTranslatorService() as service:
                service.translate_string("City", "de")

    def test_other_errors_not_retried(self):
        self.error = ValueError("invalid destination language")
        self.failures = 1
        with self.assertRaises(ValueError):
            with GoogleTranslatorService() as service:
                service.translate_string("City", "xx")
        self.assertEqual(1, len(FakeGoogletransTranslator.instances))


class GoogleClientConfigTestCase(TestCase):
    def test_client_raises_on_rejected_requests(self):
        FakeGoogletransTranslator.instances = []
        with mock.patch("googletrans.Translator", FakeGoogletransTranslator):
            with GoogleTranslatorService():
                pass
        self.assertEqual(
            {"raise_exception": True}, FakeGoogletransTranslator.instances[0].kwargs
        )

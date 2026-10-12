import shutil
import tempfile
from unittest import mock
from pathlib import Path

import polib
from django.core.management import CommandError, call_command
from django.test import TestCase

from autotranslate.management.commands.autotranslate import Command
from autotranslate.protect.guards import TokenGuard
from autotranslate.protect.segments import serialize
from autotranslate.services import TranslatorService

DATA_DIR = Path(__file__).parent / "data"


class FakeTranslatorService(TranslatorService):
    """Upper-cases strings and tags them with the target language."""

    def translate_string(self, text, target_language, source_language="en"):
        return f"[{target_language}] {text.upper()}"

    def translate_strings(self, strings, target_language, source_language="en"):
        for text in strings:
            yield self.translate_string(text, target_language, source_language)


class POFileTestCase(TestCase):
    def setUp(self):
        self.cmd = Command()
        self.cmd.service = TranslatorService()
        self.cmd.retranslate = False
        self.cmd.set_fuzzy = False
        self.po = polib.pofile(str(DATA_DIR / "django.po"))

    def sources(self):
        return [
            message.source for message in self.cmd.get_messages_to_translate(self.po)
        ]

    def test_should_read_single(self):
        self.assertIn("Location", self.sources())

    def test_should_update_single(self):
        entry = self.po[0]
        messages = [self.cmd.service.protect(entry.msgid)]
        self.cmd.update_translations([entry], messages, ["XXXX"])
        self.assertEqual("XXXX", entry.msgstr)
        self.assertTrue(entry.translated())

    def test_should_read_plural(self):
        self.assertIn("City", self.sources())
        self.assertIn("Cities", self.sources())

    def test_should_update_plural(self):
        entry = self.po[1]
        messages = [
            self.cmd.service.protect(entry.msgid),
            self.cmd.service.protect(entry.msgid_plural),
        ]
        self.cmd.update_translations([entry], messages, ["SINGULAR", "PLURAL"])
        self.assertEqual("", entry.msgstr)
        self.assertEqual("SINGULAR", entry.msgstr_plural[0])
        self.assertEqual(
            ["PLURAL"] * (len(entry.msgstr_plural) - 1),
            [v for k, v in entry.msgstr_plural.items() if k != 0],
        )
        self.assertTrue(entry.translated())

    def test_skips_translated_unless_retranslate(self):
        self.po[0].msgstr = "Ort"
        self.assertNotIn("Location", self.sources())
        self.cmd.retranslate = True
        self.assertIn("Location", self.sources())

    def test_flags_select_formats(self):
        entry = polib.POEntry(msgid="100%% of %(n)d", flags=["python-format"])
        po = polib.POFile()
        po.append(entry)
        self.assertEqual(
            "100__x0__ of __x1__", self.cmd.get_messages_to_translate(po)[0].encoded
        )


class TranslateMessagesCommandTestCase(TestCase):
    service = f"{__name__}.FakeTranslatorService"

    def setUp(self):
        self.locale_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.locale_dir)
        for lang in ["de", "es"]:
            messages = self.locale_dir / lang / "LC_MESSAGES"
            messages.mkdir(parents=True)
            shutil.copy(DATA_DIR / "django.po", messages / "django.po")

    def po(self, lang):
        return polib.pofile(str(self.locale_dir / lang / "LC_MESSAGES" / "django.po"))

    def test_translate_all_locales(self):
        call_command(
            "autotranslate",
            "--path",
            str(self.locale_dir),
            "--service",
            self.service,
        )
        for lang in ["de", "es"]:
            po = self.po(lang)
            self.assertEqual(f"[{lang}] LOCATION", po[0].msgstr)
            self.assertEqual(f"[{lang}] CITY", po[1].msgstr_plural[0])
            self.assertEqual(f"[{lang}] CITIES", po[1].msgstr_plural[1])
            self.assertNotIn("fuzzy", po[0].flags)

    def test_translate_one_locale_fuzzy(self):
        call_command(
            "autotranslate",
            "--path",
            str(self.locale_dir),
            "--service",
            self.service,
            "--locale",
            "es",
            "--set-fuzzy",
        )
        self.assertEqual("", self.po("de")[0].msgstr)
        es = self.po("es")
        self.assertEqual("[es] LOCATION", es[0].msgstr)
        self.assertIn("fuzzy", es[0].flags)

    def test_invalid_service(self):
        from django.core.exceptions import ImproperlyConfigured

        with self.assertRaises(ImproperlyConfigured):
            call_command(
                "autotranslate",
                "--path",
                str(self.locale_dir),
                "--service",
                "autotranslate.config.language_codes",
            )


class GoogleLanguageMapTestCase(TestCase):
    def test_service_language(self):
        from autotranslate.services import GoogleTranslatorService

        service = GoogleTranslatorService()
        self.assertEqual("de", service.service_language("de"))
        self.assertEqual("pt", service.service_language("pt-br"))
        self.assertEqual("zh-cn", service.service_language("zh-hans"))
        self.assertEqual("zh-tw", service.service_language("zh-hant"))
        self.assertEqual("no", service.service_language("nb"))
        self.assertIsNone(service.service_language("sr-latn"))
        self.assertIsNone(service.service_language("ia"))


class LocaleHandlingTestCase(TestCase):
    service = f"{__name__}.FakeTranslatorService"

    def setUp(self):
        self.locale_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.locale_dir)

    def make_po(self, locale, entries):
        messages = self.locale_dir / locale / "LC_MESSAGES"
        messages.mkdir(parents=True)
        po = polib.POFile()
        for msgid in entries:
            po.append(polib.POEntry(msgid=msgid, msgstr=""))
        po.save(str(messages / "django.po"))

    def read_po(self, locale):
        return polib.pofile(str(self.locale_dir / locale / "LC_MESSAGES" / "django.po"))

    def translate(self, *args):
        call_command(
            "autotranslate",
            "--path",
            str(self.locale_dir),
            "--service",
            self.service,
            *args,
        )

    def test_locale_folder_converted_to_language_code(self):
        self.make_po("pt_BR", ["Hello"])
        self.translate()
        self.assertEqual("[pt-br] HELLO", self.read_po("pt_BR")[0].msgstr)

    def test_locale_filter_accepts_locale_or_language(self):
        for locale_arg in ["pt-br", "pt_BR"]:
            with self.subTest(locale_arg=locale_arg):
                shutil.rmtree(self.locale_dir)
                self.make_po("pt_BR", ["Hello"])
                self.make_po("de", ["Hello"])
                self.translate("-l", locale_arg)
                self.assertEqual("[pt-br] HELLO", self.read_po("pt_BR")[0].msgstr)
                self.assertEqual("", self.read_po("de")[0].msgstr)

    def test_unsupported_language_skipped(self):
        self.make_po("ia", ["Hello"])
        self.make_po("de", ["Hello"])
        with mock.patch.object(
            FakeTranslatorService,
            "service_language",
            lambda self, language: None if language == "ia" else language,
        ):
            self.translate()
        self.assertEqual("", self.read_po("ia")[0].msgstr)
        self.assertEqual("[de] HELLO", self.read_po("de")[0].msgstr)

    def test_mismatched_placeholders_discarded(self):
        class UnguardedGuard(TokenGuard):
            """Sends placeholders as they are, so the fake service upper cases them."""

            def encode(self, segments):
                return serialize(segments)

        self.make_po("de", ["Hello {name}", "Hello %(name)s", "Plain"])
        with mock.patch.object(FakeTranslatorService, "guard", UnguardedGuard()):
            self.translate()
        po = self.read_po("de")
        self.assertEqual("", po[0].msgstr)
        self.assertEqual("", po[1].msgstr)
        self.assertEqual("[de] PLAIN", po[2].msgstr)

    def test_html_and_placeholders(self):
        messages = self.locale_dir / "de" / "LC_MESSAGES"
        messages.mkdir(parents=True)
        po = polib.POFile()
        po.append(
            polib.POEntry(
                msgid='Read <a href="%(url)s">the docs</a>, %(name)s',
                msgstr="",
                flags=["python-format"],
            )
        )
        po.save(str(messages / "django.po"))
        self.translate()
        self.assertEqual(
            '[de] READ <a href="%(url)s">THE DOCS</a>, %(name)s',
            self.read_po("de")[0].msgstr,
        )

    def test_translation_count_mismatch(self):
        for delta, counts in [
            (-1, "expected 3, received 2"),
            (1, "expected 3, received 4"),
        ]:
            with self.subTest(delta=delta):
                shutil.rmtree(self.locale_dir, ignore_errors=True)
                self.make_po("de", ["One", "Two", "Three"])

                def translate_strings(
                    service, strings, target_language, source_language="en", delta=delta
                ):
                    strings = list(strings)
                    yield from strings[:delta] if delta < 0 else strings + ["extra"]

                with mock.patch.object(
                    FakeTranslatorService, "translate_strings", translate_strings
                ):
                    with self.assertRaisesMessage(CommandError, counts):
                        self.translate()
                self.assertEqual("", self.read_po("de")[0].msgstr)

    def make_plural_po(self):
        messages = self.locale_dir / "de" / "LC_MESSAGES"
        messages.mkdir(parents=True)
        po = polib.POFile()
        po.append(
            polib.POEntry(
                msgid="One file",
                msgid_plural="%(count)d files",
                msgstr_plural={0: "", 1: ""},
                flags=["python-format"],
            )
        )
        po.save(str(messages / "django.po"))

    def test_plural_with_placeholders(self):
        self.make_plural_po()
        self.translate()
        entry = self.read_po("de")[0]
        self.assertEqual("[de] ONE FILE", entry.msgstr_plural[0])
        self.assertEqual("[de] %(count)d FILES", entry.msgstr_plural[1])

    def test_plural_discarded_if_one_form_lost(self):
        self.make_plural_po()
        original = FakeTranslatorService.restore

        def restore(service, message, translation):
            if message.source.startswith("%(count)d"):
                return None
            return original(service, message, translation)

        with mock.patch.object(FakeTranslatorService, "restore", restore):
            self.translate()
        entry = self.read_po("de")[0]
        self.assertEqual("", entry.msgstr_plural[0])
        self.assertEqual("", entry.msgstr_plural[1])


class FuzzyHandlingTestCase(TestCase):
    """
    Entry states:
        empty           - no translation
        changed         - makemessages marked it fuzzy because the source changed
        pending review  - fuzzy without a previous msgid (e.g. a --set-fuzzy draft)
        translated      - translated and not fuzzy
    """

    service = f"{__name__}.FakeTranslatorService"

    def setUp(self):
        self.locale_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.locale_dir)
        self.po_path = self.locale_dir / "de" / "LC_MESSAGES" / "django.po"
        self.po_path.parent.mkdir(parents=True)
        po = polib.POFile()
        po.append(polib.POEntry(msgid="empty", msgstr=""))
        po.append(
            polib.POEntry(
                msgid="changed new",
                msgstr="old translation",
                flags=["fuzzy", "python-format"],
                previous_msgid="changed old",
            )
        )
        po.append(
            polib.POEntry(msgid="pending review", msgstr="draft", flags=["fuzzy"])
        )
        po.append(polib.POEntry(msgid="translated", msgstr="done"))
        po.append(
            polib.POEntry(
                msgid="plural changed",
                msgid_plural="plurals changed",
                msgstr_plural={0: "old", 1: "olds"},
                flags=["fuzzy"],
                previous_msgid="plural old",
                previous_msgid_plural="plurals old",
            )
        )
        po.save(str(self.po_path))

    def translate(self, *args):
        call_command(
            "autotranslate",
            "--path",
            str(self.locale_dir),
            "--service",
            self.service,
            *args,
        )
        return {entry.msgid: entry for entry in polib.pofile(str(self.po_path))}

    def assert_shipped(self, entry, translation):
        self.assertEqual(translation, entry.msgstr)
        self.assertNotIn("fuzzy", entry.flags)
        self.assertIsNone(entry.previous_msgid)

    def assert_for_review(self, entry, translation):
        self.assertEqual(translation, entry.msgstr)
        self.assertIn("fuzzy", entry.flags)
        self.assertIsNone(entry.previous_msgid)

    def test_default(self):
        entries = self.translate()
        self.assert_shipped(entries["empty"], "[de] EMPTY")
        self.assert_shipped(entries["changed new"], "[de] CHANGED NEW")
        # other flags are preserved
        self.assertIn("python-format", entries["changed new"].flags)
        self.assertEqual("draft", entries["pending review"].msgstr)
        self.assertIn("fuzzy", entries["pending review"].flags)
        self.assertEqual("done", entries["translated"].msgstr)

        plural = entries["plural changed"]
        self.assertEqual(
            {0: "[de] PLURAL CHANGED", 1: "[de] PLURALS CHANGED"}, plural.msgstr_plural
        )
        self.assertNotIn("fuzzy", plural.flags)
        self.assertIsNone(plural.previous_msgid)
        self.assertIsNone(plural.previous_msgid_plural)

    def test_set_fuzzy(self):
        entries = self.translate("--set-fuzzy")
        self.assert_for_review(entries["empty"], "[de] EMPTY")
        self.assert_for_review(entries["changed new"], "[de] CHANGED NEW")
        self.assertEqual("draft", entries["pending review"].msgstr)
        self.assertEqual("done", entries["translated"].msgstr)
        self.assertNotIn("fuzzy", entries["translated"].flags)

    def test_drafts_not_retranslated(self):
        self.translate("--set-fuzzy")
        # a second run leaves the drafts made by the first one alone
        with mock.patch.object(
            FakeTranslatorService, "translate_strings"
        ) as translate_strings:
            entries = self.translate("--set-fuzzy")
        translate_strings.assert_not_called()
        self.assert_for_review(entries["empty"], "[de] EMPTY")

    def test_retranslate(self):
        entries = self.translate("--retranslate")
        for msgid in ["empty", "changed new", "pending review", "translated"]:
            self.assert_shipped(entries[msgid], f"[de] {msgid.upper()}")

    def test_retranslate_set_fuzzy(self):
        entries = self.translate("--retranslate", "--set-fuzzy")
        for msgid in ["empty", "changed new", "pending review", "translated"]:
            self.assert_for_review(entries[msgid], f"[de] {msgid.upper()}")


class ProgressBarTestCase(TestCase):
    service = f"{__name__}.FakeTranslatorService"

    def setUp(self):
        self.locale_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.locale_dir)
        for lang in ["de", "es"]:
            messages = self.locale_dir / lang / "LC_MESSAGES"
            messages.mkdir(parents=True)
            shutil.copy(DATA_DIR / "django.po", messages / "django.po")

    def translate(self, *args, terminal=True):
        import contextlib
        import io

        class Terminal(io.StringIO):
            def isatty(self):
                return True

        stdout = io.StringIO()
        stderr = Terminal() if terminal else io.StringIO()
        with contextlib.redirect_stderr(stderr):
            call_command(
                "autotranslate",
                "--path",
                str(self.locale_dir),
                "--service",
                self.service,
                *args,
                stdout=stdout,
            )
        return stdout.getvalue(), stderr.getvalue()

    def test_progress(self):
        stdout, stderr = self.translate()
        # 3 strings per file (Location, City, Cities) x 2 files
        self.assertIn("Total: 100%", stderr)
        self.assertIn("6/6", stderr)
        # a bar for each language beneath the total
        self.assertIn("German:   0%", stderr)
        self.assertIn("Spanish:   0%", stderr)
        # the per file messages are replaced by the progress bar
        self.assertNotIn("Translating", stdout)
        po = polib.pofile(str(self.locale_dir / "es" / "LC_MESSAGES" / "django.po"))
        self.assertEqual("[es] LOCATION", po[0].msgstr)

    def test_no_progress(self):
        stdout, stderr = self.translate("--no-progress")
        self.assertNotIn("%", stderr)
        self.assertEqual(2, stdout.count("Translating"))

    def test_no_terminal(self):
        stdout, stderr = self.translate(terminal=False)
        self.assertNotIn("%", stderr)
        self.assertEqual(2, stdout.count("Translating"))

    def test_without_tqdm(self):
        with mock.patch(
            "autotranslate.management.commands.autotranslate.find_spec",
            return_value=None,
        ):
            stdout, stderr = self.translate()
        self.assertNotIn("%", stderr)
        self.assertEqual(2, stdout.count("Translating"))

    def test_messages_with_progress(self):
        # messages written while the bar is shown still reach the output
        shutil.rmtree(self.locale_dir / "es")
        with mock.patch.object(
            FakeTranslatorService, "restore", lambda self, message, translation: None
        ):
            stdout, stderr = self.translate()
        self.assertIn("because its placeholders or markup changed", stdout)
        self.assertIn("100%", stderr)

    def test_language_bar_covers_all_language_files(self):
        shutil.copy(
            DATA_DIR / "django.po",
            self.locale_dir / "de" / "LC_MESSAGES" / "djangojs.po",
        )
        _, stderr = self.translate()
        self.assertIn("Total: 100%", stderr)
        self.assertIn("9/9", stderr)
        # one bar for both of the German files
        self.assertEqual(1, stderr.count("German:   0%"))
        self.assertIn("0/6", stderr)


class PluralFormsTestCase(TestCase):
    service = f"{__name__}.FakeTranslatorService"

    def test_all_plural_forms_filled(self):
        # Django's Spanish catalog declares 3 plural forms, but makemessages only
        # creates 2 msgstr[n] entries - every declared form must be translated
        locale_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, locale_dir)
        po_path = locale_dir / "es" / "LC_MESSAGES" / "django.po"
        po_path.parent.mkdir(parents=True)
        po = polib.POFile()
        po.metadata = {
            "Content-Type": "text/plain; charset=UTF-8",
            "Plural-Forms": (
                "nplurals=3; plural=n == 1 ? 0 : n != 0 && n % 1000000 == 0 ? 1 : 2;"
            ),
        }
        po.append(
            polib.POEntry(
                msgid="%(count)d file",
                msgid_plural="%(count)d files",
                msgstr_plural={0: "", 1: ""},
                flags=["python-format"],
            )
        )
        po.append(
            polib.POEntry(
                msgid="%(count)d page",
                msgid_plural="%(count)d pages",
                msgstr_plural={0: "una", 1: "varias"},
                flags=["python-format"],
            )
        )
        po.save(str(po_path))

        call_command(
            "autotranslate", "--path", str(locale_dir), "--service", self.service
        )

        entries = polib.pofile(str(po_path))
        self.assertEqual(
            {
                0: "[es] %(count)d FILE",
                1: "[es] %(count)d FILES",
                2: "[es] %(count)d FILES",
            },
            entries[0].msgstr_plural,
        )
        # translated entries are left alone
        self.assertEqual({0: "una", 1: "varias"}, entries[1].msgstr_plural)

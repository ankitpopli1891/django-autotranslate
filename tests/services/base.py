"""
Live tests of the paid translation services. These make real (billed) API requests,
so they are deselected by default - run them with ``just test-service <service>``.

Each test translates a copy of tests/service_app, which has about 250 characters of
messages, into a handful of languages chosen to exercise the language code mapping.
"""

import gettext
import shutil
import tempfile
from pathlib import Path

import polib
import pytest
from django.core.management import call_command
from django.test import TestCase, override_settings

from autotranslate.config import get_translator
from autotranslate.protect.guards import same_opaques
from autotranslate.protect.parse import parse

APP_DIR = Path(__file__).parent.parent / "service_app"

# locale (folder name) -> Django language code
LOCALES = {"de": "de", "pt_BR": "pt-br", "zh_Hans": "zh-hans"}


@pytest.mark.service
class ServiceTestMixin:
    """
    Subclasses set ``backend`` and implement ``options()``, which should return the
    service's OPTIONS from the environment or fail with a helpful message.
    """

    backend: str

    def options(self) -> dict:
        raise NotImplementedError

    # languages a service does not support, and the code they map to otherwise
    expected_languages = {
        "de": "de",
        "pt-br": "pt",
        "zh-hans": None,  # set by subclasses
        "sr-latn": None,
        "ia": None,
    }

    def setUp(self):
        settings = override_settings(
            AUTOTRANSLATE_SERVICE={"BACKEND": self.backend, "OPTIONS": self.options()}
        )
        settings.enable()
        self.addCleanup(settings.disable)

        self.work_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.work_dir)
        self.app_dir = self.work_dir / "service_app"
        shutil.copytree(APP_DIR, self.app_dir)
        self.locale_dir = self.app_dir / "locale"
        self.locale_dir.mkdir()

    def run_in_app(self, *args, **kwargs):
        import os

        cwd = os.getcwd()
        os.chdir(self.app_dir)
        try:
            call_command(*args, **kwargs)
        finally:
            os.chdir(cwd)

    def test_language_codes(self):
        service = get_translator()
        for language, expected in self.expected_languages.items():
            with self.subTest(language=language):
                self.assertEqual(expected, service.service_language(language))

    def test_translate_app(self):
        self.run_in_app("makemessages", locale=list(LOCALES), verbosity=0)
        call_command(
            "autotranslate",
            "--path",
            str(self.locale_dir),
            # the default --service is read from settings when the command module
            # is imported, so name the configured service explicitly
            "--service",
            self.backend,
            "--no-progress",
        )

        discarded = []
        total = 0
        for locale in LOCALES:
            po = polib.pofile(
                str(self.locale_dir / locale / "LC_MESSAGES" / "django.po")
            )
            for entry in po:
                total += 1
                with self.subTest(locale=locale, msgid=entry.msgid):
                    self.assertNotIn("fuzzy", entry.flags)
                    if entry.msgid_plural:
                        forms = list(entry.msgstr_plural.values())
                        sources = [entry.msgid] + [entry.msgid_plural] * (
                            len(forms) - 1
                        )
                    else:
                        forms, sources = [entry.msgstr], [entry.msgid]
                    # translations with mismatched placeholders are discarded and
                    # left empty - services sometimes translate the placeholder
                    # tokens (e.g. Google: "Saved __item__" -> "Item salvo")
                    if not any(forms):
                        discarded.append((locale, entry.msgid))
                        continue
                    for source, translation in zip(sources, forms):
                        self.assertTrue(translation)
                        self.assertNotRegex(translation, r"&(#\d+|amp|quot|lt|gt);")
                        self.assertTrue(
                            same_opaques(
                                parse(source, entry.flags),
                                parse(translation, entry.flags),
                            ),
                            f"placeholders differ: {source!r} -> {translation!r}",
                        )

        # a few discards are expected, many would mean placeholder handling broke
        self.assertLessEqual(len(discarded), total // 4, discarded)

        self.run_in_app("compilemessages", verbosity=0)
        from tests.service_app.messages import messages

        english = messages("Ada", 3)
        for locale in LOCALES:
            with self.subTest(locale=locale):
                catalog = gettext.translation(
                    "django", self.locale_dir, languages=[locale]
                )
                with pytest.MonkeyPatch.context() as patch:
                    patch.setattr("tests.service_app.messages._", catalog.gettext)
                    patch.setattr(
                        "tests.service_app.messages.ngettext", catalog.ngettext
                    )
                    translated = messages("Ada", 3)
                # the placeholders format and the messages are translated
                self.assertEqual(len(english), len(translated))
                self.assertNotEqual(english[0], translated[0])
                self.assertIn("Ada", translated[1])
                self.assertIn("3", translated[3])
                self.assertIn("3", translated[4])
                # the markup and the attribute value survive translation
                self.assertIn('href="/docs"', translated[5])
                self.assertIn("<a ", translated[5])
                self.assertIn("</a>", translated[5])


def require_env(*names: str) -> None:
    import os

    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        pytest.fail(
            f"Set {', '.join(missing)} in the environment to run this test.",
            pytrace=False,
        )

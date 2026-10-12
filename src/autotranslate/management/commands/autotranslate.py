import os
import re
import sys
import typing as t
from contextlib import contextmanager
from functools import cached_property
from importlib.util import find_spec
from pathlib import Path

import polib
from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import CommandError
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext, to_language
from django_typer.completers.apps import app_labels
from django_typer.completers.path import directories, import_paths
from django_typer.completers.settings import languages
from django_typer.management import TyperCommand
from django_typer.parsers.apps import app_config
from typer import Option

from ...config import (
    SERVICE_SETTING,
    get_service_import_path,
    get_translator,
    language_codes,
)
from ...protect.pipeline import Protected
from ...services import TranslatorService


def plural_forms(po: polib.POFile) -> int:
    """
    The number of plural forms declared by the message file's Plural-Forms header.

    :param po: The message file
    :return: The number of plural forms, or 0 if it is not declared
    """
    match = re.search(r"nplurals\s*=\s*(\d+)", po.metadata.get("Plural-Forms", ""))
    return int(match.group(1)) if match else 0


class MessageFile(t.NamedTuple):
    """A message file with entries that need translating."""

    path: Path
    language: str
    """The Django language code (e.g. pt-br)"""
    service_language: str
    """The translation service's code for the language"""
    po: polib.POFile
    messages: list[Protected]
    """The messages to translate, prepared by the translation service"""


class Command(TyperCommand, rich_markup_mode="markdown"):
    """
    The ``autotranslate`` management command. See :ref:`reference-command` for its
    options. Subclasses can override the methods below to change which messages are
    translated and how translations are written.
    """

    help = format_lazy(
        _(
            "Machine translate the message (.po) files created by {makemessages}. "
            "Only new and changed messages are translated. Translates the locale "
            "directories given with {path} and {app}, or those in {locale_paths} if "
            "neither is given."
        ),
        path="--path",
        app="--app",
        makemessages=(
            "[makemessages]"
            "(https://docs.djangoproject.com/en/stable/ref/django-admin/#django-admin-makemessages)"
        ),
        locale_paths=(
            "[LOCALE_PATHS]"
            "(https://docs.djangoproject.com/en/stable/ref/settings/#locale-paths)"
        ),
    )

    locale: list[str]
    retranslate: bool = False
    set_fuzzy: bool = False
    source_language: str = "en"

    to_translate: list[Path]

    service: TranslatorService
    show_progress: bool = False
    # the active tqdm progress bars, if any
    progress: t.Any = None
    language_progress: t.Any = None

    @cached_property
    def language_codes(self) -> dict[str, str]:
        return language_codes()

    def handle(
        self,
        paths: t.Annotated[
            list[Path] | None,
            Option(
                "--path",
                "-p",
                help=t.cast(
                    str,
                    _("A locale directory to translate (can be given more than once)."),
                ),
                shell_complete=directories,
            ),
        ] = None,
        apps: t.Annotated[
            list[AppConfig] | None,
            Option(
                "--app",
                "-a",
                help=t.cast(
                    str,
                    _(
                        "An app whose messages to translate (can be given more than once)."
                    ),
                ),
                parser=app_config,
                shell_complete=app_labels,
            ),
        ] = None,
        locale: t.Annotated[
            list[str] | None,
            Option(
                "--locale",
                "-l",
                help=t.cast(
                    str,
                    _(
                        "Only translate this locale, e.g. pt_BR or pt-br (can be given "
                        "more than once). By default every locale found is translated."
                    ),
                ),
                shell_complete=languages,
            ),
        ] = None,
        retranslate: t.Annotated[
            bool,
            Option(
                "--retranslate",
                "-r",
                help=t.cast(
                    str,
                    _(
                        "Translate all messages again, including translated messages "
                        "and messages awaiting review."
                    ),
                ),
            ),
        ] = retranslate,
        set_fuzzy: t.Annotated[
            bool,
            Option(
                "--set-fuzzy",
                "-f",
                help=t.cast(
                    str,
                    _(
                        "Mark machine translations as fuzzy so they can be reviewed "
                        "before use (fuzzy entries are not compiled by default)."
                    ),
                ),
            ),
        ] = set_fuzzy,
        source_language: t.Annotated[
            str,
            Option(
                "--source-language",
                "-s",
                help=t.cast(str, _("The language the messages are written in.")),
                shell_complete=languages,
            ),
        ] = source_language,
        service: t.Annotated[
            str,
            Option(
                "--service",
                help=t.cast(
                    str,
                    format_lazy(
                        _("The translation service to use instead of {setting}."),
                        setting=f"settings.{SERVICE_SETTING}",
                    ),
                ),
                shell_complete=import_paths,
            ),
        ] = get_service_import_path(),
        no_progress: t.Annotated[
            bool,
            Option(
                "--no-progress",
                help=t.cast(
                    str,
                    _(
                        "Do not show a progress bar. A progress bar is shown when the "
                        "tqdm package is installed and the output is a terminal."
                    ),
                ),
            ),
        ] = False,
    ):
        if not getattr(settings, "USE_I18N", False):
            raise ImproperlyConfigured(
                _("Translation is disabled. Set {setting} in your settings.").format(
                    setting="USE_I18N = True"
                )
            )

        self.service = get_translator(service, source="--service")
        self.show_progress = (
            not no_progress and sys.stderr.isatty() and find_spec("tqdm") is not None
        )
        self.locale = locale or []
        self.retranslate = retranslate
        self.set_fuzzy = set_fuzzy
        self.source_language = source_language
        self.to_translate = list(paths or [])
        for app in apps or []:
            # get locale path from app directory
            # and add it to the list of paths
            self.to_translate.append(Path(app.path) / "locale")

        if not self.to_translate:
            self.to_translate = [
                Path(pth) for pth in getattr(settings, "LOCALE_PATHS", [])
            ]

        if not self.to_translate:
            raise CommandError(
                _(
                    "No locale directories to translate. Use {path} or {app}, or set "
                    "{setting}."
                ).format(path="--path", app="--app", setting="settings.LOCALE_PATHS")
            )

        # use the service as a context manager so it can reuse resources (e.g.
        # network clients) across all of the files we translate
        with self.service:
            message_files = [
                message_file
                for directory in self.to_translate
                for message_file in self.find_message_files(directory)
            ]
            # a language may have more than one message file (e.g. djangojs.po)
            by_language: dict[str, list[MessageFile]] = {}
            for message_file in message_files:
                by_language.setdefault(message_file.language, []).append(message_file)

            with self.progress_bar(sum(len(mf.messages) for mf in message_files)):
                for language, files in by_language.items():
                    with self.language_progress_bar(
                        language, sum(len(mf.messages) for mf in files)
                    ):
                        for message_file in files:
                            self.translate_file(message_file)

    @contextmanager
    def progress_bar(self, total: int) -> t.Generator[None, None, None]:
        """
        Show a progress bar of all the strings translated while in this context, if
        progress bars are enabled.

        :param total: The total number of strings that will be translated
        """
        if not (self.show_progress and total):
            yield
            return

        from tqdm import tqdm

        with tqdm(
            total=total,
            desc=pgettext("progress bar", "Total"),
            unit=pgettext("progress bar", "messages"),
            position=0,
        ) as self.progress:
            try:
                yield
            finally:
                self.progress = None

    @contextmanager
    def language_progress_bar(
        self, language: str, total: int
    ) -> t.Generator[None, None, None]:
        """
        Show a progress bar of the strings translated for a language beneath the
        total progress bar, while in this context. The bar is removed when the
        language is finished.

        :param language: The Django language code being translated
        :param total: The number of strings that will be translated for the language
        """
        if self.progress is None:
            yield
            return

        from tqdm import tqdm

        with tqdm(
            total=total,
            desc=str(self.language_codes.get(language, language)),
            unit=pgettext("progress bar", "messages"),
            position=1,
            leave=False,
        ) as self.language_progress:
            try:
                yield
            finally:
                self.language_progress = None

    def message(self, message, **style):
        """
        Write a message to the console without disrupting the progress bar.

        :param message: The message to write
        :param style: The style parameters to pass to secho
        """
        if self.progress is None:
            self.secho(message, **style)
        else:
            with self.progress.external_write_mode():
                self.secho(message, **style)

    def find_message_files(self, directory: Path) -> t.Iterator[MessageFile]:
        """
        Find the message files under the given locale directory that have entries
        that need translating.

        :param directory: The locale directory to search for message files
        :yield: The message files to translate
        """
        if not directory.exists():
            self.message(
                _("The locale directory {directory} does not exist.").format(
                    directory=directory
                ),
                fg="red",
            )
            return

        for root_dir, _dirs, files in os.walk(directory):
            root = Path(root_dir)
            for file in files:
                if not file.endswith(".po"):
                    # process file only
                    # if its a pot file
                    continue

                # get the locale from the <locale>/LC_MESSAGES/ folder name
                locale_name = root.parent.name
                language = to_language(locale_name)

                if (
                    self.locale
                    and locale_name not in self.locale
                    and language not in self.locale
                ):
                    self.message(
                        _("Skipping {locale}: not selected with {option}.").format(
                            locale=locale_name, option="--locale"
                        ),
                        fg="yellow",
                    )
                    continue

                po_file = root / file
                service_language = self.service.service_language(language)
                if service_language is None:
                    self.message(
                        _(
                            "Skipping {file}: {service} does not support {language}."
                        ).format(
                            file=po_file,
                            service=self.service.__class__.__name__,
                            language=language,
                        ),
                        fg="yellow",
                    )
                    continue

                po = polib.pofile(po_file)
                messages = self.get_messages_to_translate(po)
                if messages:
                    yield MessageFile(po_file, language, service_language, po, messages)

    def translate_file(self, message_file: MessageFile):
        """
        Translate the given message file and save it.

        :param message_file: The message file to translate
        """
        # when shown, the progress bars show which language is being translated
        if self.progress is None:
            self.secho(
                _("Translating {file} into {target_language}").format(
                    file=message_file.path,
                    target_language=self.language_codes.get(
                        message_file.language, message_file.language
                    ),
                ),
                fg="blue",
            )

        # translate the strings,
        # all the translated strings are returned
        # in the same order on the same index
        # viz. [a, b] -> [trans_a, trans_b]
        translated_strings = self.service.translate_strings(
            [message.encoded for message in message_file.messages],
            message_file.service_language,
            self.source_language,
        )
        self.update_translations(
            message_file.po,
            message_file.messages,
            self.track(translated_strings),
            plural_forms=plural_forms(message_file.po),
        )
        message_file.po.save()

    def track(self, translated_strings: t.Iterable[str]) -> t.Iterator[str]:
        """
        Advance the progress bars as translated strings are consumed.

        :param translated_strings: The translated strings
        :yield: The translated strings
        """
        for translated in translated_strings:
            # count each string when the service returns it - updating after the
            # yield would miss the last string, which is never followed by a next()
            for bar in [self.progress, self.language_progress]:
                if bar is not None:
                    bar.update(1)
            yield translated

    def need_translate(self, entry: polib.POEntry) -> bool:
        """
        Should the given entry be machine translated?

        Entries are translated if they have no translation, or if makemessages marked
        them fuzzy because their source string changed (it records the previous
        msgid when it does this). Other fuzzy entries are awaiting review (e.g.
        drafts made with --set-fuzzy) and are left alone unless --retranslate is
        given.

        :param entry: The message file entry
        :return: True if the entry should be translated
        """
        if entry.obsolete:
            return False
        if self.retranslate:
            return True
        if entry.fuzzy:
            return bool(entry.previous_msgid or entry.previous_msgid_plural)
        return not entry.translated()

    def get_messages_to_translate(self, po: polib.POFile) -> list[Protected]:
        """
        Prepare the messages in the message file that need translating. Plural
        entries add their singular and plural messages.

        :param po: The message file
        :return: The prepared messages
        """
        messages = []
        for entry in po:
            if not self.need_translate(entry):
                continue
            messages.append(self.service.protect(entry.msgid, entry.flags))
            if entry.msgid_plural:
                messages.append(self.service.protect(entry.msgid_plural, entry.flags))
        return messages

    def update_translations(
        self,
        entries: t.Iterable[polib.POEntry],
        messages: t.Iterable[Protected],
        translated_strings: t.Iterable[str],
        plural_forms: int = 0,
    ):
        """
        Update the entries with their translations.

        :param entries: The entries to translate
        :param messages: The prepared messages, as returned by
            :meth:`get_messages_to_translate` for the entries
        :param translated_strings: The service's translations of the messages
        :param plural_forms: The number of plural forms the message file's language
            has. Plural entries are given at least this many forms.
        """
        prepared = iter(messages)
        translations = iter(translated_strings)
        sent = received = 0

        def mismatch(received: int, sent: int) -> CommandError:
            return CommandError(
                _(
                    "{service} returned the wrong number of translations: expected "
                    "{sent}, received {received}."
                ).format(
                    service=self.service.__class__.__name__,
                    received=received,
                    sent=sent,
                )
            )

        def next_pair() -> tuple[Protected, str]:
            nonlocal sent, received
            # messages must come from get_messages_to_translate for these same
            # entries, otherwise this raises StopIteration
            message = next(prepared)
            sent += 1
            try:
                translation = next(translations)
            except StopIteration:
                sent += sum(1 for _message in prepared)
                raise mismatch(received, sent) from None
            received += 1
            return message, translation

        for entry in entries:
            if not self.need_translate(entry):
                continue

            if entry.msgid_plural:
                singular = self.restore(*next_pair())
                plural = self.restore(*next_pair())
                if singular is None or plural is None:
                    continue

                # fill the first plural form with the entry.msgid translation
                entry.msgstr_plural[0] = singular

                # fill the rest of the plural forms with the entry.msgid_plural
                # translation - makemessages may create fewer forms than the
                # language's Plural-Forms header declares
                for k in range(1, max(plural_forms, len(entry.msgstr_plural))):
                    entry.msgstr_plural[k] = plural
            else:
                translation = self.restore(*next_pair())
                if translation is None:
                    continue
                entry.msgstr = translation

            # this is now a translation of the current source string
            entry.previous_msgid = None
            entry.previous_msgid_plural = None
            entry.previous_msgctxt = None

            # fuzzy entries are not compiled, so they will not be used until they
            # have been reviewed and the flag removed
            if self.set_fuzzy:
                if "fuzzy" not in entry.flags:
                    entry.flags.append("fuzzy")
            elif "fuzzy" in entry.flags:
                entry.flags.remove("fuzzy")

        extra = sum(1 for _translation in translations)
        if extra:
            raise mismatch(received + extra, sent)

    def restore(self, message: Protected, translation: str) -> str | None:
        """
        Restore the placeholders and markup in a translation, warning if the
        translation must be discarded because they did not survive translation.

        :param message: The prepared message
        :param translation: The service's translation of the message
        :return: The translated message, or None if it was discarded
        """
        restored = self.service.restore(message, translation)
        if restored is None:
            self.message(
                _(
                    "Discarded the translation of {source} because its placeholders "
                    "or markup changed: {translation}"
                ).format(source=repr(message.source), translation=repr(translation)),
                fg="yellow",
            )
        return restored

import logging
import os
import re
from optparse import make_option

import polib
from django.conf import settings
from django.core.management.base import BaseCommand

from autotranslate.utils import get_translator

logger = logging.getLogger(__name__)

# not sure whether we actually need this
# just making this change for backward compatibility
# it was always empty anyways
# https://github.com/django/django/blob/1.9/django/core/management/base.py#L210
default_options = () if not hasattr(BaseCommand, 'option_list') \
    else BaseCommand.option_list


class Command(BaseCommand):
    help = ('autotranslate all the message files that have been generated '
            'using the `makemessages` command.')

    option_list = default_options + (
        make_option('--locale', '-l', default=[], dest='locale', action='append',
                    help='autotranslate the message files for the given locale(s) (e.g. pt_BR). '
                         'can be used multiple times.'),
        make_option('--untranslated', '-u', default=False, dest='skip_translated', action='store_true',
                    help='autotranslate the fuzzy and empty messages only.'),
        make_option('--set-fuzzy', '-f', default=False, dest='set_fuzzy', action='store_true',
                    help='set the fuzzy flag on autotranslated messages.'),
        make_option('--source-language', '-s', default='en', dest='source_language', action='store',
                    help='override the default source language (en) used for translation.'),
    )

    def add_arguments(self, parser):
        # Previously, only the standard optparse library was supported and
        # you would have to extend the command option_list variable with optparse.make_option().
        # See: https://docs.djangoproject.com/en/1.8/howto/custom-management-commands/#accepting-optional-arguments
        # In django 1.8, these custom options can be added in the add_arguments()
        parser.add_argument('--locale', '-l', default=[], dest='locale', action='append',
                            help='autotranslate the message files for the given locale(s) (e.g. pt_BR). '
                                 'can be used multiple times.')
        parser.add_argument('--untranslated', '-u', default=False, dest='skip_translated', action='store_true',
                            help='autotranslate the fuzzy and empty messages only.')
        parser.add_argument('--set-fuzzy', '-f', default=False, dest='set_fuzzy', action='store_true',
                            help='set the fuzzy flag on autotranslated messages.')
        parser.add_argument('--source-language', '-s', default='en', dest='source_language', action='store',
                            help='override the default source language (en) used for translation.')

    def set_options(self, **options):
        self.locale = options['locale']
        self.skip_translated = options['skip_translated']
        self.set_fuzzy = options['set_fuzzy']
        self.source_language = options['source_language']

    def handle(self, *args, **options):
        self.set_options(**options)

        assert getattr(settings, 'USE_I18N', False), 'i18n framework is disabled'
        assert getattr(settings, 'LOCALE_PATHS', []), 'locale paths is not configured properly'
        for directory in settings.LOCALE_PATHS:
            # walk through all the paths
            # and find all the pot files
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if not file.endswith('.po'):
                        # process file only
                        # if its a pot file
                        continue

                    # get the target language from the parent folder name
                    target_language = os.path.basename(os.path.dirname(root))

                    if self.locale and target_language not in self.locale:
                        logger.info('skipping translation for locale `{}`'.format(target_language))
                        continue

                    self.translate_file(root, file, target_language)

    def translate_file(self, root, file_name, target_language):
        """
        convenience method for translating a pot file

        :param root:            the absolute path of folder where the file is present
        :param file_name:       name of the file to be translated (it should be a pot file)
        :param target_language: language in which the file needs to be translated
        """
        logger.info('filling up translations for locale `{}`'.format(target_language))

        po = polib.pofile(os.path.join(root, file_name))
        strings = self.get_strings_to_translate(po)

        # translate the strings,
        # all the translated strings are returned
        # in the same order on the same index
        # viz. [a, b] -> [trans_a, trans_b]
        tl = get_translator()
        translated_strings = tl.translate_strings(strings, target_language, self.source_language, False)
        self.update_translations(po, translated_strings)
        po.save()

    def need_translate(self, entry):
        return not entry.obsolete and (not (self.skip_translated and entry.translated()))

    def get_strings_to_translate(self, po):
        """Return list of string to translate from po file.

        :param po: POFile object to translate
        :type po: polib.POFile
        :return: list of string to translate
        :rtype: collections.Iterable[six.text_type]
        """
        strings = []
        for index, entry in enumerate(po):
            if not self.need_translate(entry):
                continue
            strings.append(humanize_placeholders(entry.msgid))
            if entry.msgid_plural:
                strings.append(humanize_placeholders(entry.msgid_plural))
        return strings

    def update_translations(self, entries, translated_strings):
        """Update translations in entries.

        The order and number of translations should match to get_strings_to_translate() result.

        :param entries: list of entries to translate
        :type entries: collections.Iterable[polib.POEntry] | polib.POFile
        :param translated_strings: list of translations
        :type translated_strings: collections.Iterable[six.text_type]
        """
        translations = iter(translated_strings)
        for entry in entries:
            if not self.need_translate(entry):
                continue

            if entry.msgid_plural:
                # fill the first plural form with the entry.msgid translation
                translation = next(translations)
                translation = fix_translation(entry.msgid, translation)
                entry.msgstr_plural[0] = translation

                # fill the rest of plural forms with the entry.msgid_plural translation
                translation = next(translations)
                translation = fix_translation(entry.msgid_plural, translation)
                for k, v in entry.msgstr_plural.items():
                    if k != 0:
                        entry.msgstr_plural[k] = translation
            else:
                translation = next(translations)
                translation = fix_translation(entry.msgid, translation)
                entry.msgstr = translation

            # Set the 'fuzzy' flag on translation
            if self.set_fuzzy and 'fuzzy' not in entry.flags:
                entry.flags.append('fuzzy')


def humanize_placeholders(msgid):
    """Convert placeholders to the (google translate) service friendly form.

    %(name)s -> __name__
    %s       -> __item__
    %d       -> __number__
    """
    return re.sub(
        r'%(?:\((\w+)\))?([sd])',
        lambda match: r'__{0}__'.format(
            match.group(1).lower() if match.group(1) else 'number' if match.group(2) == 'd' else 'item'),
        msgid)


def restore_placeholders(msgid, translation):
    """Restore placeholders in the translated message."""
    placehoders = re.findall(r'(\s*)(%(?:\(\w+\))?[sd])(\s*)', msgid)
    return re.sub(
        r'(\s*)(__[\w]+?__)(\s*)',
        lambda matches: '{0}{1}{2}'.format(placehoders[0][0], placehoders[0][1], placehoders.pop(0)[2]),
        translation)


def fix_translation(msgid, translation):
    # Google Translate removes a lot of formatting, these are the fixes:
    # - Add newline in the beginning if msgid also has that
    if msgid.startswith('\n') and not translation.startswith('\n'):
        translation = u'\n' + translation

    # - Add newline at the end if msgid also has that
    if msgid.endswith('\n') and not translation.endswith('\n'):
        translation += u'\n'

    # Remove spaces that have been placed between %(id) tags
    translation = restore_placeholders(msgid, translation)
    return translation

import logging
import os
import polib
import re

from autotranslate.utils import translate_strings

from django.conf import settings
from django.core.management.base import BaseCommand

from optparse import make_option

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = ('autotranslate all the message files that have been generated '
            'using the `makemessages` command.')

    option_list = BaseCommand.option_list + (
        make_option('--locale', '-l', default=[], dest='locale', action='append',
                    help='autotranslate the message files for the given locale(s) (e.g. pt_BR). '
                         'can be used multiple times.'),
    )

    def add_arguments(self, parser):
        # Previously, only the standard optparse library was supported and
        # you would have to extend the command option_list variable with optparse.make_option().
        # See: https://docs.djangoproject.com/en/1.8/howto/custom-management-commands/#accepting-optional-arguments
        # In django 1.8, these custom options can be added in the add_arguments()
        parser.add_argument('--locale', '-l', default=[], dest='locale', action='append',
                            help='autotranslate the message files for the given locale(s) (e.g. pt_BR). '
                                 'can be used multiple times.')

    def handle(self, *args, **options):
        locale = options.get('locale')
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

                    if locale and target_language not in locale:
                        logger.info('skipping translation for locale `{}`'.format(target_language))
                        continue

                    self.translate_file(root, file, target_language)

    @classmethod
    def translate_file(cls, root, file_name, target_language):
        """
        convenience method for translating a pot file

        :param root:            the absolute path of folder where the file is present
        :param file_name:       name of the file to be translated (it should be a pot file)
        :param target_language: language in which the file needs to be translated
        """
        logger.info('filling up translations for locale `{}`'.format(target_language))

        po = polib.pofile(os.path.join(root, file_name))
        strings = []
        translations = {}
        for index, entry in enumerate(po):
            strings.append(entry.msgid)
            translations.update({index: entry.msgstr})

        # translate the strings,
        # all the translated strings are returned
        # in the same order on the same index
        # viz. [a, b] -> [trans_a, trans_b]
        translated_strings = translate_strings(strings, target_language, 'en', False)

        for index, entry in enumerate(po):
            # Google Translate removes a lot of formatting, these are the fixes:
            # - Add newline in the beginning if msgid also has that
            if entry.msgid.startswith('\n') and not translated_strings[index].startswith('\n'):
                translated_strings[index] = u'\n' + translated_strings[index]

            # - Add newline at the end if msgid also has that
            if entry.msgid.endswith('\n') and not translated_strings[index].endswith('\n'):
                translated_strings[index] += u'\n'

            # Remove spaces that have been placed between %(id) tags
            translated_strings[index] = re.sub('%\s*\(\s*(\w+)\s*\)\s*s',
                                               lambda match: r'%({})s'.format(match.group(1).lower()),
                                               translated_strings[index])

            entry.msgstr = translated_strings[index]

        po.save()

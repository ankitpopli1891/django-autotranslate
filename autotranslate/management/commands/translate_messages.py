from autotranslate.utils import translate_strings

from django.conf import settings
from django.core.management.base import BaseCommand

from optparse import make_option

import os


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
                        return

                    # get the target language from the parent folder name
                    target_language = os.path.basename(os.path.dirname(root))

                    if locale and target_language not in locale:
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
        print('translating ', target_language)

        strings = []
        translations = {}
        with open(os.path.join(root, file_name)) as _input_file:
            original_file = _input_file.readlines()
            for index, line in enumerate(original_file):
                if line.startswith('msgid'):
                    # separate the actual string from the whole line
                    # for each line in input file
                    strings.append('"'.join(line.split('"')[1:-1]))
                if line.startswith('msgstr'):
                    # map the line number with the raw string
                    # taken out for translation
                    translations.update({
                        index: line
                    })

        # translate the strings,
        # all the translated strings are returned
        # in the same order on the same index
        # viz. [a, b] -> [trans_a, trans_b]
        translated_strings = translate_strings(strings, target_language, 'en', False)

        # sort the numbers to make sure all the translations
        # are injected at the right position
        keys = [_ for _ in translations.keys()]
        keys.sort()

        index = 0
        for key in keys:
            line = translations.get(key).split('"')
            line = [line[0], line[-1]]
            line.insert(1, translated_strings[index])
            line = '"'.join(line)
            translations[key] = line
            index += 1

        with open(os.path.join(root, file_name), 'w') as output_file:
            for index, line in enumerate(original_file):
                if index in translations.keys():
                    line = translations.get(index)
                    output_file.write(line)
                    continue
                output_file.write(line)
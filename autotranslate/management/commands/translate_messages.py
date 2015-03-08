from autotranslate.utils import translate_strings

from django.conf import settings
from django.core.management.base import BaseCommand

import os


class Command(BaseCommand):
    help = 'autotranslate all the po files that have been generated'

    def handle(self, *args, **options):
        for directory in settings.LOCALE_PATHS:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith('.po'):
                        target_language = os.path.basename(os.path.dirname(root))
                        self._translate_file(root, file, target_language)

    def _translate_file(self, root, file, target_language):
        # TODO
        # FIXME
        _strings = []
        _translations = {}
        _file = os.path.join(root, file)
        with open(_file) as _input_file:
            _original_file = _input_file.readlines()
            for index, line in enumerate(_original_file):
                if line.startswith('msgid'):
                    # separate the actual string from the whole line
                    # for each line in input file
                    _strings.append('"'.join(line.split('"')[1:-1]))
                if line.startswith('msgstr'):
                    _translations.update({
                        index: line
                    })

        # translate the strings
        _translated_strings = translate_strings(_strings, target_language, 'en', False)
        _index = 0
        _keys = [_ for _ in _translations.keys()]
        _keys.sort()
        for key in _keys:
            _line = _translations.get(key).split('"')
            _line = [_line[0], _line[-1]]
            _line.insert(1, _translated_strings[_index])
            _line = '"'.join(_line)
            _translations[key] = _line
            _index += 1

        with open(_file, 'w') as _output_file:
            for index, line in enumerate(_original_file):
                if index in _translations.keys():
                    line = _translations.get(index)
                    _output_file.write(line)
                    continue
                _output_file.write(line)
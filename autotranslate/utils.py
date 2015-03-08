import collections
import goslate

go_slate = goslate.Goslate()


def translate_string(text, target_language, source_language='en'):
    return go_slate.translate(text, target_language, source_language)


def translate_strings(strings, target_language, source_language='en', optimized=True):
    """
    :param strings:         an iterable (list, tuple,etc)
    :param target_language: language code of the target language
    :param source_language: language code of the source language
    :param optimized:       accepts boolean
    :return:                if `optimized` is true returns a generator else an array of translated strings
    """
    if not isinstance(strings, collections.Iterable):
        raise Exception
    _translations = go_slate.translate(strings, target_language, source_language)
    return _translations if optimized else [_ for _ in _translations]
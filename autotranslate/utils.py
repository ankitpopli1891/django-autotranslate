import collections

from django.conf import settings


# google-api-python-client is optional
try:
    import googleapiclient
except ImportError:
    googleapiclient = None


if hasattr(settings, 'GOOGLE_TRANSLATE_KEY'):
    assert googleapiclient, '`GOOGLE_TRANSLATE_KEY` is configured, but `google-api-python-client` is not installed'
    from googleapiclient.discovery import build
    gt_service = build('translate', 'v2', developerKey=settings.GOOGLE_TRANSLATE_KEY)
else:
    import goslate
    go_slate = goslate.Goslate()


def translate_string(text, target_language, source_language='en'):
    if hasattr(settings, 'GOOGLE_TRANSLATE_KEY'):
        return_dict = gt_service.translations().list(
            source=source_language, 
            target=target_language,
            q=[text]
        ).execute()
        return return_dict['translations'][0]['translatedText'] 
    else:
        return go_slate.translate(text, target_language, source_language)


def translate_strings(strings, target_language, source_language='en', optimized=True):
    """
    :param strings:         an iterable (list, tuple, etc)
    :param target_language: language code of the target language
    :param source_language: language code of the source language
    :param optimized:       accepts boolean
    :return:                if `optimized` is true returns a generator else an array of translated strings
    """
    if not isinstance(strings, collections.Iterable):
        raise Exception
    if hasattr(settings, 'GOOGLE_TRANSLATE_KEY'):
        return_dict = gt_service.translations().list(
            source=source_language,
            target=target_language,
            q=strings
        ).execute()
        return [t['translatedText'] for t in return_dict['translations']]
    else:
        _translations = go_slate.translate(strings, target_language, source_language)
        return _translations if optimized else [_ for _ in _translations]

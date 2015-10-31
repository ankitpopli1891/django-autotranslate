import collections
import six

from autotranslate.compat import goslate, googleapiclient

from django.conf import settings


class BaseTranslatorService:
    """
    Defines the base methods that should be implemented
    """

    def translate_string(self, text, target_language, source_language='en'):
        """
        Returns a single translated string literal for the target language.
        """
        raise NotImplementedError('.translate_string() must be overridden.')

    def translate_strings(self, strings, target_language, source_language='en', optimized=True):
        """
        Returns a iterator containing translated strings for the target language
        in the same order as in the strings.
        :return:    if `optimized` is True returns a generator else an array
        """
        raise NotImplementedError('.translate_strings() must be overridden.')


class GoSlateTranslatorService(BaseTranslatorService):
    """
    Uses the free web-based API for translating.
    https://bitbucket.org/zhuoqiang/goslate
    """

    def __init__(self):
        assert goslate, '`GoSlateTranslatorService` requires `goslate` package'
        self.service = goslate.Goslate()

    def translate_string(self, text, target_language, source_language='en'):
        assert isinstance(text, six.string_types), '`text` should a string literal'
        return self.service.translate(text, target_language, source_language)

    def translate_strings(self, strings, target_language, source_language='en', optimized=True):
        assert isinstance(strings, collections.Iterable), '`strings` should a iterable containing string_types'
        translations = self.service.translate(strings, target_language, source_language)
        return translations if optimized else [_ for _ in translations]


class GoogleAPITranslatorService(BaseTranslatorService):
    """
    Uses the paid Google API for translating.
    https://github.com/google/google-api-python-client
    """

    def __init__(self):
        assert googleapiclient, '`GoogleAPITranslatorService` requires `google-api-python-client` package'

        self.developer_key = getattr(settings, 'GOOGLE_TRANSLATE_KEY', None)
        assert self.developer_key, ('`GOOGLE_TRANSLATE_KEY` is not configured, '
                                    'it is required by `GoogleAPITranslatorService`')

        from googleapiclient.discovery import build
        self.service = build('translate', 'v2', developerKey=self.developer_key)

    def translate_string(self, text, target_language, source_language='en'):
        assert isinstance(text, six.string_types), '`text` should a string literal'
        response = self.service.translations() \
            .list(source=source_language, target=target_language, q=[text]).execute()
        return response.get('translations').pop(0).get('translatedText')

    def translate_strings(self, strings, target_language, source_language='en', optimized=True):
        assert isinstance(strings, collections.Iterable), '`strings` should a iterable containing string_types'
        assert not optimized, 'optimized=True is not supported in `GoogleAPITranslatorService`'
        response = self.service.translations() \
            .list(source=source_language, target=target_language, q=strings).execute()
        return [t.get('translatedText') for t in response.get('translations')]

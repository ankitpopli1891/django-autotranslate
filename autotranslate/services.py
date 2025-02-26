import collections
import six
from autotranslate.compat import googletrans, googleapiclient, boto3

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


class GoogleTranslatorService(BaseTranslatorService):
    """
    Uses the free web-based API for translating.
    https://github.com/ssut/py-googletrans
    """

    def __init__(self):
        assert googletrans, '`TranslateTranslatorService` requires `translate` package'
        self.service = googletrans.Translator()

    def translate_string(self, text, target_language, source_language='en'):
        assert isinstance(text, six.string_types), '`text` should a string literal'
        return self.service.translate(text,dest=target_language,src=source_language).text

    def translate_strings(self, strings, target_language, source_language='en', optimized=True):
        assert isinstance(strings, collections.abc.Iterable), '`strings` should a iterable containing string_types'
        translations =  self.service.translate(list(strings),dest=target_language,src=source_language)
        return [item.text for item in translations]


class GoogleAPITranslatorService(BaseTranslatorService):
    """
    Uses the paid Google API for translating.
    https://github.com/google/google-api-python-client
    """

    def __init__(self, max_segments=128):
        assert googleapiclient, '`GoogleAPITranslatorService` requires `google-api-python-client` package'

        self.developer_key = getattr(settings, 'GOOGLE_TRANSLATE_KEY', None)
        assert self.developer_key, ('`GOOGLE_TRANSLATE_KEY` is not configured, '
                                    'it is required by `GoogleAPITranslatorService`')

        from googleapiclient.discovery import build
        self.service = build('translate', 'v2', developerKey=self.developer_key)

        # the google translation API has a limit of max
        # 128 translations in a single request
        # and throws `Too many text segments Error`
        self.max_segments = max_segments
        self.translated_strings = []

    def translate_string(self, text, target_language, source_language='en'):
        assert isinstance(text, six.string_types), '`text` should a string literal'
        response = self.service.translations() \
            .list(source=source_language, target=target_language, q=[text]).execute()
        return response.get('translations').pop(0).get('translatedText')

    def translate_strings(self, strings, target_language, source_language='en', optimized=True):
        try: 
            assert isinstance(strings, collections.MutableSequence), \
                '`strings` should be a sequence containing string_types'
        except:
            assert isinstance(strings, collections.abc.MutableSequence)
            assert not optimized, 'optimized=True is not supported in `GoogleAPITranslatorService`'
        if len(strings) == 0:
            return []
        elif len(strings) <= self.max_segments:
            setattr(self, 'translated_strings', getattr(self, 'translated_strings', []))
            response = self.service.translations() \
                .list(source=source_language, target=target_language, q=strings).execute()
            self.translated_strings.extend([t.get('translatedText') for t in response.get('translations')])
            return self.translated_strings
        else:
            self.translate_strings(strings[0:self.max_segments], target_language, source_language, optimized)
            _translated_strings = self.translate_strings(strings[self.max_segments:],
                                                         target_language, source_language, optimized)

            # reset the property or it will grow with subsequent calls
            self.translated_strings = []
            return _translated_strings


class AmazonTranslateTranslatorService(BaseTranslatorService):
    """
    Uses the paid Amazon Translate for translating.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/translate.html
    """

    def __init__(self,):
        assert boto3, '`AmazonTranslateTranslatorService` requires the `boto3` package'

        self.service = boto3.client('translate')

    def translate_string(self, text, target_language, source_language='en'):
        assert isinstance(text, six.string_types), '`text` should a string literal'
        response = self.service.translate_text(
            Text=text,
            SourceLanguageCode=source_language,
            TargetLanguageCode=target_language
        )
        return response['TranslatedText']

    def translate_strings(self, strings, target_language, source_language='en', optimized=False):
        assert isinstance(strings, collections.MutableSequence), \
            '`strings` should be a sequence containing string_types'
        translated = []
        for text in strings:
            translated.append(
                self.translate_string(text, target_language, source_language)
            )
        return translated

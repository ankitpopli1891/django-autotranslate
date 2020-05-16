import collections, six, json, requests
import logging
logger = logging.getLogger(__name__)

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
        assert isinstance(strings, collections.MutableSequence), \
            '`strings` should be a sequence containing string_types'
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


class GoogleWebTranslatorService(BaseTranslatorService):
    """
    Uses the Google Translation Web Service.
    'https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh&&dt=t&q=%s'
    """

    def __init__(self, max_segments=256):
        self.max_segments = max_segments

    def webtranslate(self, strings, target_language, source_language='en'):
        from urllib.parse import quote
        import requests, re

        translated_strings = []
        HEADERS = {'Accept-Language': 'en-US,en;q=0.5',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0',
                   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                   'Connection': 'keep-alive',
                   'Accept-Encoding': 'gzip, deflate, br'}
        for string in strings:
            url = 'https://translate.googleapis.com/translate_a/single?client=gtx&sl={}&tl={}&&dt=t&q={}'.format(source_language, target_language, quote(string))
            response = requests.get(url, headers=HEADERS)
            match = re.compile('\[\[\["(.*?)","').findall(str(response.content, 'utf-8'))
            if match:
                translated_strings.append(match[0])
                logger.info('Translate "{}" to "{}"'.format(string, match[0]))
            else:
                logger.info('Translate "{}" denied from google. Please try again later.'.format(string))
        return translated_strings

    def translate_string(self, text, target_language, source_language='en'):
        assert isinstance(text, six.string_types), '`text` should a string literal'
        response = self.webtranslate(strings=[text], target=target_language, source=source_language)
        return response

    def translate_strings(self, strings, target_language, source_language='en', optimized=True):
        assert isinstance(strings, collections.MutableSequence), '`strings` should be a sequence containing string_types'

        if len(strings) == 0:
            logger.info('There are no strings request to translate for "{}".'.format(target_language))
            return []
        elif len(strings) <= self.max_segments:
            setattr(self, 'translated_strings', getattr(self, 'translated_strings', []))
            response = self.webtranslate(strings=strings, target_language=target_language, source_language=source_language)
            if response:
                return response
            else:
                return []
        else:
            # reset the property or it will grow with subsequent calls
            return []


class AzureAPITranslatorService(BaseTranslatorService):
    """
    Use Azure Translator Text
    https://docs.microsoft.com/en-us/azure/cognitive-services/translator/reference/v3-0-reference
    """

    def __init__(self, max_segments=256):
        self.azure_translator_secret_key = getattr(settings, 'AZURE_TRANSLATOR_SECRET_KEY', None)
        assert self.azure_translator_secret_key, ('`AZURE_TRANSLATOR_SECRET_KEY` is not configured, it is required by `Azure Translator`')

        self.max_segments = max_segments

    def azure_translate(self, strings, target_language, source_language='en'):
        from urllib.parse import quote
        import requests, re

        translated_strings = []
        headers = {'Ocp-Apim-Subscription-Key': self.azure_translator_secret_key,
                   'Content-type': 'application/json'}
        for string in strings:
            base_url = 'https://api.cognitive.microsofttranslator.com/'
            path = 'translate?api-version=3.0&'
            params = 'from={}&to={}'.format(source_language, target_language)
            url = '{}{}{}'.format(base_url, path, params)
            data = [{'Text': string}]
            response = requests.post(url, headers=headers, json=data)
            response = response.json()
            if response[0]['translations']:
                translated_strings.append(response[0]['translations'][0]['text'])
                logger.info('Translate "{}" to "{}"'.format(string, response[0]['translations'][0]['text']))
            else:
                logger.info('Didn\'t get translate for "{}" from Azure.'.format(string))
        return translated_strings

    def translate_string(self, text, target_language, source_language='en'):
        assert isinstance(text, six.string_types), '`text` should a string literal'
        response = self.azure_translate(strings=[text], target=target_language, source=source_language)
        return response

    def translate_strings(self, strings, target_language, source_language='en', optimized=True):
        assert isinstance(strings, collections.MutableSequence), '`strings` should be a sequence containing string_types'

        if len(strings) == 0:
            logger.info('There are no strings request to translate for "{}".'.format(target_language))
            return []
        elif len(strings) <= self.max_segments:
            setattr(self, 'translated_strings', getattr(self, 'translated_strings', []))
            response = self.azure_translate(strings=strings, target_language=target_language, source_language=source_language)
            if response:
                return response
            else:
                return []
        else:
            # reset the property or it will grow with subsequent calls
            return []

import os

from .base import ServiceTestMixin, TestCase, require_env


class GoogleAPITranslatorServiceTests(ServiceTestMixin, TestCase):
    """
    Requires GOOGLE_TRANSLATE_API_KEY.
    """

    backend = "autotranslate.services.GoogleAPITranslatorService"
    expected_languages = {
        **ServiceTestMixin.expected_languages,
        "pt": "pt-PT",
        "zh-hans": "zh-CN",
        "zh-hant": "zh-TW",
        "nb": "no",
    }

    def options(self):
        require_env("GOOGLE_TRANSLATE_API_KEY")
        return {"api_key": os.environ["GOOGLE_TRANSLATE_API_KEY"]}

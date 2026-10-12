from .base import ServiceTestMixin, TestCase, require_env


class AmazonTranslateTranslatorServiceTests(ServiceTestMixin, TestCase):
    """
    Uses boto3's standard configuration - credentials and region come from the
    environment (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION) or
    from your ~/.aws config files.
    """

    backend = "autotranslate.services.AmazonTranslateTranslatorService"
    expected_languages = {
        **ServiceTestMixin.expected_languages,
        "pt": "pt-PT",
        "zh-hans": "zh",
        "zh-hant": "zh-TW",
        "nb": "no",
        # Amazon's Serbian is Latin script and its es is European Spanish
        "sr": None,
        "sr-latn": "sr",
        "es-ar": "es-MX",
    }

    def options(self):
        import boto3

        session = boto3.Session()
        if session.get_credentials() is None:
            require_env("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")
        if session.region_name is None:
            require_env("AWS_DEFAULT_REGION")
        return {}

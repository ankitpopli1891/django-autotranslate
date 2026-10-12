import asyncio
import contextlib
import time
import typing as t
from functools import cached_property

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext as _

from .protect.guards import Guard, HTMLGuard, TokenGuard
from .protect.pipeline import Protected, protect, restore


class ServiceUnavailable(Exception):
    """
    Raised when a translation service refuses or fails to fulfil a request (e.g. it
    is rate limiting us).
    """


class TranslatorService:
    """
    Defines the base methods that should be implemented

    Services are configured by the ``OPTIONS`` in
    ``settings.AUTOTRANSLATE_SERVICE``, which are passed to the service's
    constructor as keyword arguments.

    Services are also context managers. Callers that make multiple translation
    calls should use the service in a ``with`` block so that services that hold
    resources (e.g. network clients) can set them up once and tear them down when
    finished. Subclasses that need this should override :meth:`__enter__` and
    :meth:`__exit__`, and must still work when used outside of a ``with`` block.
    """

    default_language_map: t.ClassVar[dict[str, str | None]] = {}
    """
    Django language codes that do not map onto the service's language codes by the
    rules in :meth:`~autotranslate.services.TranslatorService.service_language`. None marks languages the service does not
    support.
    """

    guard: t.ClassVar[Guard] = TokenGuard()
    """
    How placeholders and markup are protected while messages are translated. The
    default replaces them with numbered tokens. Services that translate HTML and
    honour ``translate="no"`` should use
    :class:`~autotranslate.protect.guards.HTMLGuard`.

    The guard is shared by all instances of the service class, so custom guards
    must not keep per-call state on ``self``. Custom guards subclass
    :class:`~autotranslate.protect.guards.Guard`, implement ``encode`` and
    ``decode`` and set ``content_type``.
    """

    def __init__(self, *, language_map: dict[str, str | None] | None = None):
        """
        :param language_map: Mappings of Django language codes to the service's
            language codes (or None if the service does not support the language).
            These are added to, or override, :attr:`default_language_map`.
        """
        self.language_map = {**self.default_language_map, **(language_map or {})}

    def __enter__(self) -> t.Self:
        """
        Acquire any resources the service needs for the duration of the block.
        """
        return self

    def supported_languages(self) -> t.Collection[str] | None:
        """
        The language codes this service supports. Override this to enable language
        code matching in :meth:`~autotranslate.services.TranslatorService.service_language`. It is called at most once per
        service instance.

        :return: The service's language codes, or None if they are not known.
        """
        return None

    @cached_property
    def _supported_languages(self) -> dict[str, str] | None:
        # lower case code -> the service's code
        supported = self.supported_languages()
        if supported is None:
            return None
        return {code.lower(): code for code in supported}

    def service_language(self, language: str) -> str | None:
        """
        Map a Django language code (e.g. ``pt-br``) to the code this service uses
        for that language. Django language codes are lower case BCP 47 language
        tags. The service's code is resolved in this order:

        1. The language map - :attr:`default_language_map` plus any
           ``language_map`` option.
        2. A case insensitive match against :meth:`supported_languages`.
        3. Dropping region subtags until a supported code is found (e.g. ``pt-br``
           -> ``pt``). Script subtags are never dropped because the result would
           be in the wrong writing system (e.g. ``sr-latn`` -> ``sr`` is Cyrillic).

        If the service's supported languages are not known, the Django language
        code is used as is.

        :param language: The Django language code
        :return: The service's code for the language, or None if the service does
            not support the language.
        """
        language = language.lower()
        language_map = {
            code.lower(): mapped
            for code, mapped in getattr(
                self, "language_map", self.default_language_map
            ).items()
        }
        if language in language_map:
            return language_map[language]

        supported = self._supported_languages
        if supported is None:
            return language

        subtags = language.split("-")
        while subtags:
            candidate = "-".join(subtags)
            if candidate in supported:
                return supported[candidate]
            # script subtags are 4 letters (ISO 15924)
            if len(subtags) == 1 or len(subtags[-1]) == 4:
                break
            subtags.pop()
        return None

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """
        Release any resources acquired in :meth:`__enter__`.
        """

    def translate_string(
        self, text: str, target_language: str, source_language: str = "en"
    ) -> str:
        """
        Returns a single translated string literal for the target language.
        """
        raise NotImplementedError(
            _("Subclasses of {base} must implement {function}().").format(
                base="TranslatorService", function="translate_string"
            )
        )

    def translate_strings(
        self,
        strings: t.Sequence[str],
        target_language: str,
        source_language: str = "en",
    ) -> t.Generator[str, None, None]:
        """
        Yields containing translated strings for the target language in the same order
        as the input strings.

        :yield: translated strings
        """
        raise NotImplementedError(
            _("Subclasses of {base} must implement {function}().").format(
                base="TranslatorService", function="translate_strings"
            )
        )

    def protect(self, text: str, flags: t.Collection[str] = ()) -> Protected:
        """
        Prepare a message for translation by this service. Send
        :attr:`~autotranslate.protect.pipeline.Protected.encoded` to the service.

        :param text: The message
        :param flags: The message's gettext flags (e.g. ``python-format``)
        """
        return protect(text, self.guard, flags)

    def restore(self, protected: Protected, translation: str) -> str | None:
        """
        Restore the placeholders and markup in this service's translation of a
        protected message.

        :param protected: The message returned by :meth:`protect`
        :param translation: The service's translation of the encoded message
        :return: The translated message, or None if placeholders or markup were
            lost or changed in translation
        """
        return restore(protected, translation)


class GoogleTranslatorService(TranslatorService):
    """
    Uses the free web-based API for translating.
    https://github.com/ssut/py-googletrans
    """

    # googletrans clients hold an httpx.AsyncClient that is bound to the event loop
    # it first runs on, so the client and the loop must share the same lifetime
    _runner: asyncio.Runner | None = None
    _translator: t.Any = None

    # how many times to retry a request that fails with a network error, and the
    # delay in seconds before the first retry (doubled for each subsequent retry)
    retries: int = 3
    retry_delay: float = 1.0
    # the delay in seconds before the first retry when Google rejects a request,
    # usually because we are being rate limited (doubled for each retry)
    rate_limit_delay: float = 30.0

    # Google's Serbian is Cyrillic only, so it cannot be used for sr-latn
    default_language_map: t.ClassVar[dict[str, str | None]] = {
        "zh-hans": "zh-cn",
        "zh-hant": "zh-tw",
        "nb": "no",
        "sr-latn": None,
    }

    def __init__(
        self,
        *,
        retries: int | None = None,
        retry_delay: float | None = None,
        rate_limit_delay: float | None = None,
        language_map: dict[str, str | None] | None = None,
    ):
        """
        :param retries: How many times to retry a request that fails because of a
            network error or because Google rejected it.
        :param retry_delay: The delay in seconds before retrying a request that
            failed because of a network error (doubled for each retry).
        :param rate_limit_delay: The delay in seconds before retrying a request that
            Google rejected, usually because of rate limiting (doubled for each
            retry).
        :param language_map: Mappings of Django language codes to Google language
            codes (or None if Google does not support the language). These are
            added to, or override, :attr:`default_language_map`.
        """
        super().__init__(language_map=language_map)
        if retries is not None:
            self.retries = retries
        if retry_delay is not None:
            self.retry_delay = retry_delay
        if rate_limit_delay is not None:
            self.rate_limit_delay = rate_limit_delay

    def supported_languages(self) -> t.Collection[str]:
        import googletrans

        return googletrans.LANGUAGES.keys()

    @staticmethod
    async def _open_translator():
        import googletrans

        # by default googletrans silently returns the untranslated text when Google
        # rejects a request, which would write the source text as the translation
        return await googletrans.Translator(raise_exception=True).__aenter__()

    @staticmethod
    async def _call(translator, text, target_language: str, source_language: str):
        try:
            return await translator.translate(
                text, dest=target_language, src=source_language
            )
        except Exception as err:
            # googletrans raises a bare Exception when Google rejects a request
            if str(err).startswith("Unexpected status code"):
                raise ServiceUnavailable(str(err)) from err
            raise

    def __enter__(self) -> t.Self:
        self._runner = asyncio.Runner()
        try:
            self._translator = self._runner.run(self._open_translator())
        except BaseException:
            self._runner.close()
            self._runner = None
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._runner is None:
            return
        try:
            self._runner.run(self._translator.__aexit__(None, None, None))
        finally:
            self._runner.close()
            self._runner = None
            self._translator = None

    def _translate(self, text, target_language: str, source_language: str):
        import httpx

        # Google drops long-lived connections and throttles bursts of requests, so
        # retry these failures with a fresh client and an increasing delay
        attempt = 0
        while True:
            try:
                return self._translate_once(text, target_language, source_language)
            except (httpx.TransportError, ServiceUnavailable) as err:
                if attempt >= self.retries:
                    raise
                delay = (
                    self.rate_limit_delay
                    if isinstance(err, ServiceUnavailable)
                    else self.retry_delay
                )
                time.sleep(delay * 2**attempt)
                attempt += 1
                if self._runner is not None:
                    self._reopen_translator()

    def _reopen_translator(self):
        import httpx

        assert self._runner is not None
        # the old connection is already broken, so errors closing it don't matter
        with contextlib.suppress(httpx.TransportError):
            self._runner.run(self._translator.__aexit__(None, None, None))
        self._translator = self._runner.run(self._open_translator())

    def _translate_once(self, text, target_language: str, source_language: str):
        if self._runner is not None:
            return self._runner.run(
                self._call(self._translator, text, target_language, source_language)
            )

        # not in a with block - use a single-use client and event loop
        async def translate_once():
            translator = await self._open_translator()
            try:
                return await self._call(
                    translator, text, target_language, source_language
                )
            finally:
                await translator.__aexit__(None, None, None)

        return asyncio.run(translate_once())

    def translate_string(
        self, text: str, target_language: str, source_language: str = "en"
    ) -> str:
        return self._translate(text, target_language, source_language).text

    def translate_strings(
        self,
        strings: t.Sequence[str],
        target_language: str,
        source_language: str = "en",
    ) -> t.Generator[str, None, None]:
        translations = self._translate(list(strings), target_language, source_language)
        return (item.text for item in translations)


class GoogleAPITranslatorService(TranslatorService):
    """
    Uses the paid Google API for translating.
    https://github.com/google/google-api-python-client
    """

    # Google translates HTML and leaves translate="no" elements alone. The guard
    # also decides the request's format, in text format the API escapes nothing
    guard = HTMLGuard()

    # Google's Serbian is Cyrillic only, so it cannot be used for sr-latn. Django's
    # pt is European Portuguese, Google's is Brazilian.
    default_language_map: t.ClassVar[dict[str, str | None]] = {
        "pt": "pt-PT",
        "zh-hans": "zh-CN",
        "zh-hant": "zh-TW",
        "nb": "no",
        "sr-latn": None,
    }

    def __init__(
        self,
        *,
        api_key: str | None = None,
        max_segments: int = 128,
        language_map: dict[str, str | None] | None = None,
    ):
        """
        :param api_key: Your Google Cloud Translation API key (required).
        :param max_segments: The maximum number of strings to send in each request.
            The API rejects requests with more than 128.
        :param language_map: Mappings of Django language codes to Google language
            codes (or None if Google does not support the language). These are
            added to, or override, :attr:`default_language_map`.
        """
        super().__init__(language_map=language_map)
        if not api_key:
            raise ImproperlyConfigured(
                _(
                    "{service} requires the {option} option. Add it to OPTIONS in "
                    "{setting}."
                ).format(
                    service=self.__class__.__name__,
                    option="api_key",
                    setting="settings.AUTOTRANSLATE_SERVICE",
                )
            )
        try:
            from googleapiclient.discovery import build
        except ImportError as ie:
            raise ImportError(
                _(
                    "{service} requires the {package} package. Install it with: "
                    "{command}"
                ).format(
                    service=self.__class__.__name__,
                    package="google-api-python-client",
                    command='pip install "django-autotranslate[google]"',
                )
            ) from ie

        self.service = build("translate", "v2", developerKey=api_key)
        self.max_segments = max_segments

    def supported_languages(self) -> t.Collection[str]:
        response = self.service.languages().list().execute()
        return [language["language"] for language in response["languages"]]

    def translate_string(
        self, text: str, target_language: str, source_language: str = "en"
    ) -> str:
        response = (
            self.service.translations()
            .list(
                source=source_language,
                target=target_language,
                q=[text],
                format=self.guard.content_type,
            )
            .execute()
        )
        return response.get("translations").pop(0).get("translatedText")

    def translate_strings(
        self,
        strings: t.Sequence[str],
        target_language: str,
        source_language: str = "en",
    ) -> t.Generator[str, None, None]:
        while strings:
            response = (
                self.service.translations()
                .list(
                    source=source_language,
                    target=target_language,
                    q=strings[: self.max_segments],
                    format=self.guard.content_type,
                )
                .execute()
            )
            yield from (t.get("translatedText") for t in response.get("translations"))
            strings = strings[self.max_segments :]


class AmazonTranslateTranslatorService(TranslatorService):
    """
    Uses the paid Amazon Translate for translating.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/translate.html
    """

    # Amazon detects HTML in the text and leaves translate="no" elements alone
    guard = HTMLGuard()

    # Amazon's Serbian is written in Latin script, it has no Cyrillic Serbian (Django's
    # sr). Django's pt is European Portuguese, Amazon's is Brazilian. Amazon's es is
    # European Spanish, es-MX is its Latin American Spanish.
    default_language_map: t.ClassVar[dict[str, str | None]] = {
        "pt": "pt-PT",
        "zh-hans": "zh",
        "zh-hant": "zh-TW",
        "nb": "no",
        "sr": None,
        "sr-latn": "sr",
        "es-ar": "es-MX",
        "es-co": "es-MX",
        "es-ni": "es-MX",
        "es-ve": "es-MX",
    }

    def __init__(
        self, *, language_map: dict[str, str | None] | None = None, **client_options
    ):
        """
        :param language_map: Mappings of Django language codes to Amazon language
            codes (or None if Amazon does not support the language). These are
            added to, or override, :attr:`default_language_map`.
        :param client_options: Passed to :func:`boto3.client` (e.g. ``region_name``,
            ``aws_access_key_id``, ``aws_secret_access_key``). Anything not given
            is found by boto3 the usual way (environment variables, ``~/.aws``
            config files, instance roles, ...).
        """
        super().__init__(language_map=language_map)
        try:
            import boto3
        except ImportError as ie:
            raise ImportError(
                _(
                    "{service} requires the {package} package. Install it with: "
                    "{command}"
                ).format(
                    service=self.__class__.__name__,
                    package="boto3",
                    command='pip install "django-autotranslate[amazon]"',
                )
            ) from ie

        self.service = boto3.client("translate", **client_options)

    def supported_languages(self) -> t.Collection[str]:
        languages: list[str] = []
        kwargs: dict[str, str] = {}
        while True:
            response = self.service.list_languages(**kwargs)
            languages.extend(lang["LanguageCode"] for lang in response["Languages"])
            if not response.get("NextToken"):
                return languages
            kwargs = {"NextToken": response["NextToken"]}

    def translate_string(
        self, text: str, target_language: str, source_language: str = "en"
    ) -> str:
        response = self.service.translate_text(
            Text=text,
            SourceLanguageCode=source_language,
            TargetLanguageCode=target_language,
        )
        return response["TranslatedText"]

    def translate_strings(
        self, strings: t.Sequence[str], target_language: str, source_language="en"
    ) -> t.Generator[str, None, None]:
        for text in strings:
            yield self.translate_string(text, target_language, source_language)

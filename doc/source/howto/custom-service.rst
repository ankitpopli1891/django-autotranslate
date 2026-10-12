.. include:: ../refs.rst

.. _howto-custom-service:

====================================
Add a translation service
====================================

To use a translation service django-autotranslate does not support, subclass
:class:`~autotranslate.services.TranslatorService` and point
:setting:`AUTOTRANSLATE_SERVICE` at your class.

Write the service
=================

A service translates a batch of strings into one language. This outline has every
part a service may provide; only :meth:`~autotranslate.services.TranslatorService.translate_strings`
is required:

.. code-block:: python

    # myproject/translation.py
    import typing as t

    from autotranslate.protect.guards import HTMLGuard
    from autotranslate.services import TranslatorService


    class ExampleTranslatorService(TranslatorService):
        # Services that translate HTML and leave translate="no" elements alone
        # should use HTMLGuard. The default sends placeholders as numbered tokens.
        guard = HTMLGuard()

        # Django language codes the matching rules get wrong for this service
        default_language_map = {"zh-hans": "zh-CN", "sr-latn": None}

        def __init__(self, *, api_key: str, language_map=None):
            # OPTIONS from AUTOTRANSLATE_SERVICE are passed as keyword arguments,
            # pass language_map on so users can override the mapping
            super().__init__(language_map=language_map)
            self.client = ExampleClient(api_key)

        def supported_languages(self) -> t.Collection[str]:
            # the service's language codes, used to match Django's codes
            return self.client.languages()

        def translate_strings(
            self,
            strings: t.Sequence[str],
            target_language: str,
            source_language: str = "en",
        ) -> t.Iterator[str]:
            # one translation for each string, in the same order
            yield from self.client.translate(
                strings, target=target_language, source=source_language, html=True
            )

``ExampleClient`` stands for your service's client library.

Things to know:

* **Strings are already protected.** ``translate_strings`` receives messages with their
  placeholders and markup encoded by the service's ``guard``, and the command restores
  and checks them afterwards. Send the strings as they are, and tell the service they
  are HTML if you use :class:`~autotranslate.protect.guards.HTMLGuard`.
* **Language codes are the service's.** ``target_language`` has already been mapped
  from Django's code, see :ref:`explanation-languages`.
* **Return exactly one translation per string.** The command stops with an error if the
  numbers differ.
* **Guards are shared.** The ``guard`` is used by every instance of the class, so a
  custom guard must not keep state between calls.
* **Hold connections in a with block.** If your service opens a connection, override
  :meth:`~autotranslate.services.TranslatorService.__enter__` and
  :meth:`~autotranslate.services.TranslatorService.__exit__`. The command uses the
  service in a ``with`` block for the whole run. The service must still work outside
  one.

Use it
======

.. code-block:: python

    AUTOTRANSLATE_SERVICE = {
        "BACKEND": "myproject.translation.ExampleTranslatorService",
        "OPTIONS": {"api_key": os.environ.get("EXAMPLE_API_KEY")},
    }

Test it
=======

Translate a small message file and check the results, for example with the tutorial's
messages. If translations are discarded, the service is changing placeholders or
markup: check that it honours the guard (for ``HTMLGuard``, ``translate="no"``
elements). Run with ``--set-fuzzy`` while you test, so nothing is used unreviewed.

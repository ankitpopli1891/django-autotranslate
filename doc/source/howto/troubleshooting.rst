.. include:: ../refs.rst

.. _howto-troubleshooting:

===============
Troubleshooting
===============

Messages
========

``Translation is disabled. Set USE_I18N = True in your settings.``
    django-autotranslate needs Django's translation system. Set :setting:`USE_I18N` to
    ``True``.

``No locale directories to translate. Use --path or --app, or set settings.LOCALE_PATHS.``
    The command did not know where your message files are. Set :setting:`LOCALE_PATHS`,
    or give the directories with ``--path`` or ``--app``.

``The locale directory ... does not exist.``
    A directory from :setting:`LOCALE_PATHS` or ``--path`` is missing. Create it and run
    :django-admin:`makemessages`.

``Skipping ...: ... does not support ....``
    The service cannot translate that language. Use another service for it, or map it
    to a language the service supports with ``language_map``, see
    :ref:`howto-languages` and :ref:`reference-languages`.

``Discarded the translation of '...' because its placeholders or markup changed: '...'``
    The service lost, changed or added a placeholder or HTML tag, so the translation was
    not used and the message stays untranslated. A few of these are normal, especially
    with the free service, which can only send placeholders as tokens in the text. Translate those
    messages by hand, or use a paid service. See :ref:`explanation-protection`.

``... returned the wrong number of translations: expected ..., received ....``
    The service returned more or fewer translations than it was sent. Nothing was
    saved for that file. This is a bug in the service: if it is a custom service, check
    that ``translate_strings`` returns one translation per string.

``... requires the ... package. Install it with: ...``
    Install the extra for your service, for example
    ``pip install "django-autotranslate[google]"``.

``Could not import the translation service ...``
    Check the import path in :setting:`AUTOTRANSLATE_SERVICE` or ``--service``.

The free service stops with ``Unexpected status code "429"``
    Google is rate limiting your IP address. See :ref:`howto-free-google`.

Translations are not used
=========================

If your site still shows the original text:

* Run :django-admin:`compilemessages`. Django uses the compiled ``.mo`` files, not the
  ``.po`` files.
* Check the entry is not marked ``fuzzy``. Fuzzy entries are not compiled, see
  :ref:`howto-review`.
* Check the language is in :setting:`LANGUAGES` and is active, for example with
  :class:`~django.middleware.locale.LocaleMiddleware`.

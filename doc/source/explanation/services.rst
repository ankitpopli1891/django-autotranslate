.. include:: ../refs.rst

.. _explanation-services:

====================
Choosing a service
====================

django-autotranslate supports three translation services. All of them protect your
placeholders and markup, and translations that come back damaged are discarded rather
than used, so the differences are in coverage, reliability, cost and set up.

.. list-table::
    :header-rows: 1
    :widths: 22 26 26 26

    * -
      - Google Translate (free)
      - Google Cloud Translation
      - Amazon Translate
    * - Django languages supported
      - 87 of 97
      - 87 of 97
      - 69 of 97
    * - Set up
      - None
      - Google Cloud project and API key
      - AWS account and credentials
    * - Cost
      - Free
      - Paid per character, with a monthly free allowance
      - Paid per character
    * - Placeholder protection
      - Numbered tokens in the text, occasionally changed
      - Marked as not to be translated
      - Marked as not to be translated
    * - Reliability
      - Unofficial, rate limited by IP address
      - Supported API
      - Supported API

Which to use
============

**To try django-autotranslate, or for an occasional run**, the free service needs no
set up. Expect the occasional translation to be discarded because a placeholder was
changed, and translate a few languages at a time to avoid being rate limited, see
:ref:`howto-free-google`.

**For regular use, Google Cloud Translation** is the best default. It covers the same
languages as the free service, protects placeholders reliably and does well in
independent quality evaluations. At the size of a typical project's messages the cost
is small, often within the free allowance.

**Amazon Translate** suits projects already on AWS, or that need its variants: it has
Latin American Spanish (``es-MX``) and Serbian in Latin script, where Google has only
European Spanish and Cyrillic Serbian. It does not support 28 of Django's languages,
including Basque, Galician, Esperanto, Belarusian, Khmer and Nepali.

You can combine services: use one for most languages and another for the languages it
does better, with a separate settings module or ``--service`` for those runs, and
``--locale`` to choose the languages.

Your messages leave your servers
================================

All three services send your messages to Google or Amazon. For most projects messages
are already public, as they appear in the site, but if yours include text that is not
yet public, check the services' terms. The paid services' terms for API data are
generally stricter than the free service's.

Quality
=======

No service is best for every language. Machine translation is weakest on short
messages without context, which are most of a typical Django project's messages, and on
tone and formality. Whichever service you use, have people who speak the language
review the translations, see :ref:`howto-review`.

Each service's language list is in :ref:`reference-languages`.

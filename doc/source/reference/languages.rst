.. include:: ../refs.rst

.. _reference-languages:

===================
Supported languages
===================

The languages Django supports, and the language code each service translates them
into. A dash means the service cannot translate the language, and its message files are
skipped. English is not listed: it is the source language of most projects.

Of Django's 97 other languages, the free Google service supports 87, Google Cloud
Translation 87 and Amazon Translate 69. :ref:`explanation-languages` explains how the
codes are matched.

The services' language lists change. This table was generated in October 2026 from the
lists the services report, with Django 6.1's :setting:`LANGUAGES`. ``autotranslate``
always uses the services' current lists.

.. include:: language_table.inc

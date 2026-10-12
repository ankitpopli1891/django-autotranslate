.. include:: ../refs.rst

.. _explanation-how:

============
How it works
============

A run of ``autotranslate``
==========================

#. **Find message files.** The command walks the locale directories (``--path``,
   ``--app`` or :setting:`LOCALE_PATHS`) for ``.po`` files. A file's language comes from
   the directory it is in: ``locale/pt_BR/LC_MESSAGES/django.po`` is Brazilian
   Portuguese (``pt-br``). Files for languages the service does not support are
   skipped.
#. **Choose messages.** In each file it picks the messages that need translating, see
   below. Files with none are skipped without contacting the service.
#. **Protect them.** Placeholders, HTML and newlines in each message are protected so
   the service cannot change them, see :ref:`explanation-protection`.
#. **Translate.** The messages of a file are sent to the service together.
#. **Restore and check.** Placeholders and markup are restored, the spacing around them
   repaired, and any translation whose placeholders or markup changed is discarded with
   a warning.
#. **Save.** The translations are written into the file, and the file saved.

The service is opened once for the whole run, so services that keep a connection reuse
it.

Which messages are translated
=============================

gettext message files record the state of each translation, and ``autotranslate``
uses it to translate only what needs translating:

.. list-table::
    :header-rows: 1
    :widths: 40 30 30

    * - Message
      - Translated by default
      - With ``--retranslate``
    * - No translation
      - Yes
      - Yes
    * - Source text changed since it was translated
      - Yes
      - Yes
    * - Awaiting review (``fuzzy``)
      - No
      - Yes
    * - Translated
      - No
      - Yes
    * - Obsolete (``#~``, no longer in the code)
      - No
      - No

When the source text of a translated message changes, :django-admin:`makemessages`
keeps the old translation, marks it fuzzy and records the old source text in a ``#|``
comment. That comment is how ``autotranslate`` tells a changed message apart from one
that is fuzzy because it is waiting for review. Translating a changed message removes the
comment.

With ``--set-fuzzy`` new translations are marked fuzzy, otherwise any fuzzy flag on a
translated message is removed so the translation is used.

Plural forms
============

Messages with plural forms (``ngettext``) have a singular and a plural source text, and
languages have one or more plural forms, declared in each file's ``Plural-Forms``
header. ``autotranslate`` translates both source texts, uses the singular's translation
for the first form and the plural's for all the others, filling every form the header
declares.

That is right for languages like German or Spanish. Languages with more plural forms,
such as Russian or Arabic, need different wording for some numbers, which a review
should correct.

What is not sent
================

Only message text is sent to the service. Message context (``pgettext``), translator
comments and the code a message comes from are not, so the service translates each
message without knowing where it is used. Short messages like "Open" or "Order" can be
ambiguous; review them.

.. include:: ../refs.rst

.. _explanation-protection:

=====================================
Protecting placeholders and markup
=====================================

Django messages contain things a translation must not change. If a service translates
``%(name)s`` into ``%(nombre)s``, the translated message raises an error when Django
formats it. django-autotranslate parses each message, hides these parts from the
service, and checks they come back unchanged.

What is protected
=================

* **Placeholders** in the formats :django-admin:`makemessages` marks with flags:
  ``python-format`` (``%(name)s``, ``%d``, ``%.2f`` and the ``%%`` escape) and
  ``python-brace-format`` (``{name}``, ``{0:>10}`` and the ``{{`` escape). Messages with
  neither flag are checked for the common placeholders of both formats.
* **HTML**: tags, comments and character references such as ``&amp;``. Text inside
  elements is translated, except inside ``code``, ``kbd``, ``pre``, ``samp``,
  ``script``, ``style`` and ``var``. Attribute values are not translated.
* **Newlines.**

How each service is told
========================

Take this message:

.. code-block:: python

    _('Hello %(name)s, read the <a href="/help/">help pages</a>.')

Paid services translate HTML and leave elements marked ``translate="no"`` alone, so
Google Cloud Translation and Amazon Translate receive it as HTML:

.. code-block:: html

    Hello <span translate="no" id="0">%(name)s</span>, read the <span id="1">help pages</span>.

The ids let the original be put back even when the translation moves things around. The
service's copy of a protected part is ignored, so a service that alters it anyway does
no harm.

The free Google service only translates plain text, so protected parts become numbered
tokens:

.. code-block:: text

    Hello __x0__, read the __x1__help pages__x2__.

The tokens are numbered rather than named after the placeholders, because the service
treats tokens that are words as words: in testing it translated ``__service__`` into
Slovenian as ``__storitev__``, but kept every numbered token. Tokens are still less
reliable than the paid services' ``translate="no"``, so the occasional translation may
be discarded.

Checking the result
===================

After a translation comes back, its protected parts are restored and the result is
parsed again. The translation is discarded, and the message left untranslated, if:

* a placeholder or tag was lost, duplicated or changed;
* the service added a placeholder or tag that is not in the source;
* tags come back in the wrong order or nesting.

A discarded translation is never written to your message files, and the command prints
a warning naming the message. Leaving a message untranslated is safe: Django shows the
source text instead.

Repairing spacing
=================

Services often add or drop spaces around protected parts, for example
``{file} :`` or ``Salvo%s``. Using the source as a guide, django-autotranslate removes
spaces added before punctuation, restores a space dropped between a word and a
placeholder (except in scripts written without spaces, like Chinese and Japanese), and
keeps the source's spacing at the start and end of the message and around newlines.
French typography's no-break spaces before punctuation are kept.

Amazon and ampersands
=====================

Amazon Translate decodes HTML entities in its input twice, so text such as ``&copy`` or
``?a=1&timestamp=2`` comes back as ``©`` or ``×tamp=2``. Words containing an ampersand
sequence that would decode like this are sent as protected parts too. Words like
``AT&T`` are not affected and are translated normally.

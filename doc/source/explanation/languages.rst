.. include:: ../refs.rst

.. _explanation-languages:

==============
Language codes
==============

Django and the translation services name languages differently, so each of Django's
language codes has to be matched to the code a service uses.

Django's codes
==============

Django identifies languages with lower case `BCP 47
<https://www.rfc-editor.org/info/bcp47>`_ language tags in :setting:`LANGUAGES`, such
as ``de``, ``pt-br`` and ``zh-hans``. They combine standard codes for:

* the language (ISO 639): ``de``, ``pt``, ``zh``;
* the writing system, or script (ISO 15924): ``zh-hans`` (Simplified Chinese),
  ``sr-latn`` (Serbian in Latin script);
* the region (ISO 3166): ``pt-br``, ``es-ar``.

Message files are kept in directories named after gettext locale names, a different
spelling of the same tag (``pt_BR``, ``zh_Hans``). ``autotranslate`` accepts either.

Why services differ
===================

The services mostly use BCP 47 too, but the standard often allows several correct tags
for the same language, and each service chose its own: Simplified Chinese is ``zh-CN``
to Google (a region) and ``zh`` to Amazon, Django's ``nb`` (Norwegian Bokmål) is ``no``
(Norwegian) to both. Services also only list the variants they have models for, and
their defaults differ: Google's and Amazon's ``pt`` is Brazilian Portuguese, while
Django's ``pt`` is European Portuguese.

How codes are matched
=====================

For each language ``autotranslate`` tries, in order:

#. **Known exceptions.** Each service has a built in map of codes the rules below get
   wrong, plus anything you add with the ``language_map`` option.
#. **The same code.** A case insensitive match against the languages the service
   reports, giving the service's spelling (``es-mx`` becomes Amazon's ``es-MX``).
#. **Without the region.** ``es-ar`` becomes ``es``, ``pt-br`` becomes ``pt``.

If none match, the service does not support the language and its files are skipped.

Scripts are never dropped: removing ``latn`` from ``sr-latn`` would give ``sr``, which
at Google is Serbian in Cyrillic script, so translations would be in the wrong
alphabet. Amazon's ``sr`` happens to be Latin script, so its built in map translates
``sr-latn`` into ``sr`` and skips Django's ``sr``, which is Cyrillic.

The built in exceptions were checked against the services' language lists and output.
:ref:`reference-languages` shows the result for every language.

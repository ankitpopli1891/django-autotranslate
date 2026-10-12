.. include:: ./refs.rst

==========
Change Log
==========

v2.0.0 (unreleased)
===================

* Rewrote the documentation as a tutorial, how-to guides, reference and explanation
  (`Diátaxis <https://diataxis.fr/>`_).
* The free Google service sends placeholders as numbered tokens (``__x0__``) instead of
  named ones (``__name__``), which Google translated as words (Slovenian
  ``__storitev__`` for ``__service__``), discarding the translation.
* Plural messages are translated into every plural form a language's
  ``Plural-Forms`` header declares. :django-admin:`makemessages` can create fewer
  forms, which left some numbers untranslated (e.g. Spanish's third form).
* **Breaking:** the ``translate_messages`` management command has been renamed to
  ``autotranslate``.
* Messages whose source string changed (marked fuzzy by ``makemessages``) are now
  retranslated, and fuzzy entries awaiting review are no longer overwritten.
  ``--set-fuzzy`` marks the new machine translations for review.
* Added a progress bar, shown when the ``progress`` extra is installed and the output
  is a terminal (``--no-progress`` turns it off).
* ``AUTOTRANSLATE_SERVICE`` may now be a dictionary with a ``BACKEND`` import path
  and ``OPTIONS`` that configure the service.
* Django language codes are matched to each service's language codes, and
  languages a service does not support are skipped. Use the ``language_map``
  option to add or override mappings.
* Fixed ``GoogleAPITranslatorService`` HTML escaping translations (e.g. ``'`` became
  ``&#39;``).
* **Breaking:** ``GOOGLE_TRANSLATE_KEY`` has been removed, set the ``api_key`` option
  of ``GoogleAPITranslatorService`` instead.
* **Breaking:** the ``AUTOTRANSLATE_TRANSLATOR_SERVICE`` setting has been removed, use
  ``AUTOTRANSLATE_SERVICE`` instead.
* Placeholders and HTML markup are parsed using each message's gettext flags and
  protected from translation, paid services are told not to translate them.
  More printf (``%.2f``, ``%i``, ``%%``) and brace (``{0:>10}``, ``{{``)
  placeholders are recognized, and spacing around placeholders is repaired.
  Translations that lose, change or add placeholders or markup are discarded with
  a warning, and the command raises an error if a service returns a different
  number of translations than it was sent.
* **Breaking:** ``TranslatorService.humanize_placeholders``,
  ``restore_placeholders``, ``validate_translation`` and ``fix_translation`` have
  been replaced by ``TranslatorService.protect`` and ``TranslatorService.restore``
  and the ``guard`` attribute. The command's API changed to match:
  ``get_strings_to_translate`` is now ``get_messages_to_translate``,
  ``check_translation`` is now ``restore``, ``update_translations`` takes
  ``(entries, messages, translated_strings)`` and ``MessageFile.strings`` is now
  ``MessageFile.messages``.

v1.3.0 (2024-08-23)
===================

v1.2.0 (2021-06-06)
===================

v1.1.1 (2020-05-06)
===================

v1.1.0 (2018-05-06)
===================

v1.0.1 (2017-01-14)
===================

v1.0.0 (2016-01-23)
===================

v0.8.0 (2016-01-02)
===================

v0.7.0 (2015-11-10)
===================

v0.6.0 (2015-11-09)
===================

v0.5.0 (2015-10-31)
===================

v0.4.0 (2015-08-07)
===================

v0.3.0 (2015-06-27)
===================

v0.2.0 (2015-04-04)
===================


v0.1.0 (2015-03-08)
===================

* Initial release.

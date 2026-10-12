.. include:: ../refs.rst

.. _reference-command:

=====================
``autotranslate``
=====================

.. django-admin:: autotranslate

.. typer:: autotranslate.management.commands.autotranslate.Command:typer_app
    :prog: django-admin autotranslate
    :width: 80
    :show-nested:
    :convert-png: latex

Options
=======

``-p``, ``--path``
    A locale directory to translate. Can be given more than once. All message files
    (``.po``) under it are translated, each in the language of its
    ``<locale>/LC_MESSAGES`` directory.

``-a``, ``--app``
    An app whose ``locale`` directory to translate. Can be given more than once. If
    neither ``--path`` nor ``--app`` is given, the directories in
    :setting:`LOCALE_PATHS` are translated.

``-l``, ``--locale``
    Only translate this locale. Accepts locale names (``pt_BR``) and language codes
    (``pt-br``). Can be given more than once. By default every locale found is
    translated.

``-r``, ``--retranslate``
    Translate all messages again, including translated messages and messages awaiting
    review. By default only untranslated messages and messages whose source text changed
    are translated, see :ref:`explanation-how`.

``-f``, ``--set-fuzzy``
    Mark machine translations as ``fuzzy``. Fuzzy entries are not compiled, so they are
    not used until someone reviews them. See :ref:`howto-review`.

``-s``, ``--source-language``
    The language the messages are written in. Defaults to ``en``.

``--service``
    The import path of the translation service to use instead of
    :setting:`AUTOTRANSLATE_SERVICE`. The ``OPTIONS`` in that setting are only used
    with the service it configures.

``--no-progress``
    Do not show a progress bar. A progress bar is shown when the ``progress`` extra is
    installed (``pip install "django-autotranslate[progress]"``) and the output is a
    terminal.

Messages that need translating are sent one file at a time. A file is only written once
all of its messages have been translated, and translations whose placeholders or markup
changed are discarded with a warning (see :ref:`explanation-protection`).

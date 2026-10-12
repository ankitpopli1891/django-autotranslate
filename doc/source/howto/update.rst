.. include:: ../refs.rst

.. _howto-update:

===================================
Keep translations up to date
===================================

As your code changes, run the same three commands each time you are ready to update
translations:

.. code-block:: console

    $ django-admin makemessages --all
    $ django-admin autotranslate
    $ django-admin compilemessages

:django-admin:`makemessages` adds new messages to every message file and marks messages
whose source text changed. ``autotranslate`` then translates:

* new messages, which have no translation yet;
* messages whose source text changed. ``makemessages`` marks these fuzzy and keeps the
  old source text, which tells ``autotranslate`` the translation is out of date.

It leaves everything else alone, including translations made by people. See
:ref:`explanation-how` for the details.

Translate everything again
==========================

To replace all translations, for example after switching to a better service, use
``--retranslate`` (``-r``):

.. code-block:: console

    $ django-admin autotranslate --retranslate

.. warning::

    ``--retranslate`` overwrites every translation, including translations made or
    corrected by people. Commit your message files first so you can review the changes.

Remove old messages
===================

``makemessages`` keeps messages that are no longer in your code as obsolete entries
(``#~``). ``autotranslate`` never translates them. Remove them with
``makemessages --no-obsolete``.

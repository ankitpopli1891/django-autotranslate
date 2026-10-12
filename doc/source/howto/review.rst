.. include:: ../refs.rst

.. _howto-review:

==============================
Review machine translations
==============================

Machine translations can be wrong, too literal or the wrong tone for your site. If
people review your translations, mark machine translations as needing review so they
are not used until someone has checked them.

Mark translations for review
============================

Run ``autotranslate`` with ``--set-fuzzy`` (``-f``):

.. code-block:: console

    $ django-admin autotranslate --set-fuzzy

Each machine translation is marked with gettext's ``fuzzy`` flag:

.. code-block:: po

    #, fuzzy, python-format
    msgid "Welcome back, %(name)s!"
    msgstr "Willkommen zurück, %(name)s!"

:django-admin:`compilemessages` leaves fuzzy entries out of the compiled files, so your
site keeps showing the original text until the translation is approved.

Review them
===========

Open the message files in a translation editor such as
`Poedit <https://poedit.net/>`_, `Weblate <https://weblate.org/>`_ or
`django-rosetta <https://github.com/mbi/django-rosetta>`_. They list fuzzy entries for
review. Correct each translation and remove its fuzzy flag (in a text editor, delete
``fuzzy`` from the ``#,`` line). Then compile:

.. code-block:: console

    $ django-admin compilemessages

Running ``autotranslate --set-fuzzy`` again leaves translations that are waiting for
review alone, so it never overwrites a reviewer's work in progress.

Approve all of them
===================

To use machine translations without review, run ``autotranslate`` without
``--set-fuzzy``. To publish drafts you already created, remove their fuzzy flags in your
editor; running ``autotranslate`` again does not do it for you.

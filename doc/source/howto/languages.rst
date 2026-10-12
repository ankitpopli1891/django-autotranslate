.. include:: ../refs.rst

.. _howto-languages:

========================
Choose which languages
========================

``autotranslate`` translates every message file it finds, whatever its language. The
languages you translate into are the ones you created message files for with
:django-admin:`makemessages`.

Translate some languages only
=============================

Pass ``--locale`` (``-l``) once for each language. Both locale names (``pt_BR``, the
directory names) and language codes (``pt-br``) work:

.. code-block:: console

    $ django-admin autotranslate -l de -l pt_BR -l zh-hans

Add a language
==============

Create its message file, then translate it:

.. code-block:: console

    $ django-admin makemessages -l ja
    $ django-admin autotranslate -l ja

Add the language to :setting:`LANGUAGES` too, so your site offers it.

Skip a language
===============

To never machine translate a language, for example one that human translators look
after, map it to ``None`` with the ``language_map`` option of your service:

.. code-block:: python

    AUTOTRANSLATE_SERVICE = {
        "BACKEND": "autotranslate.services.GoogleAPITranslatorService",
        "OPTIONS": {
            "api_key": ...,
            "language_map": {"fr": None},
        },
    }

``autotranslate`` then prints ``Skipping ...: GoogleAPITranslatorService does not
support fr.`` for its message files and leaves them alone.

Translate into a different variant
==================================

Each service maps Django's language codes onto its own, see
:ref:`explanation-languages`. To choose a different variant, map the Django code to the
service's code. For example, to translate Django's ``pt`` (European Portuguese) into
Brazilian Portuguese with Google Cloud:

.. code-block:: python

    "language_map": {"pt": "pt"}

Check :ref:`reference-languages` for the codes each service uses.

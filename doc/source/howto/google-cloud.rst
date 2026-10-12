.. include:: ../refs.rst

.. _howto-google-cloud:

=================================
Use Google Cloud Translation
=================================

`Google Cloud Translation <https://cloud.google.com/translate>`_ is a paid service. It
supports almost all of Django's languages and is told not to translate placeholders and
markup, so its translations are discarded far less often than the free service's. The
first 500,000 characters each month are free.

Get an API key
==============

#. In the `Google Cloud console <https://console.cloud.google.com/>`_, select or create
   a project and make sure billing is enabled for it.
#. Enable the **Cloud Translation API** (*APIs & Services → Library*).
#. Create an API key (*APIs & Services → Credentials → Create credentials → API key*).
#. Restrict the key to the Cloud Translation API (*API restrictions*), so a leaked key
   can only be used for translation.

Configure the service
=====================

Install the ``google`` extra:

.. code-block:: console

    $ pip install "django-autotranslate[google]"

Set :setting:`AUTOTRANSLATE_SERVICE` in your settings. Read the key from the
environment rather than committing it:

.. code-block:: python

    import os

    AUTOTRANSLATE_SERVICE = {
        "BACKEND": "autotranslate.services.GoogleAPITranslatorService",
        "OPTIONS": {
            "api_key": os.environ.get("GOOGLE_TRANSLATE_API_KEY"),
        },
    }

Then translate as usual:

.. code-block:: console

    $ GOOGLE_TRANSLATE_API_KEY=... django-admin autotranslate

If the key is missing the command stops with
``GoogleAPITranslatorService requires the api_key option``.

Use it for some runs only
=========================

Options in :setting:`AUTOTRANSLATE_SERVICE` are only used with the service configured
there, so ``--service`` cannot switch to a service that needs an API key. Instead, put
the configuration above in its own settings module that imports your main settings,
and select it for the runs that should use Google Cloud:

.. code-block:: python

    # mysite/settings_translate.py
    import os

    from .settings import *

    AUTOTRANSLATE_SERVICE = {
        "BACKEND": "autotranslate.services.GoogleAPITranslatorService",
        "OPTIONS": {"api_key": os.environ.get("GOOGLE_TRANSLATE_API_KEY")},
    }

.. code-block:: console

    $ django-admin autotranslate --settings mysite.settings_translate

See also
========

* :ref:`reference-settings` for all of the service's options.
* :ref:`explanation-services` to compare the services.

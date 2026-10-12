.. include:: ./refs.rst

.. _tutorial:

=========================
Tutorial: your first run
=========================

In this tutorial you will create a small Django project, mark a few messages for
translation, machine translate them into German and Spanish, and see the translations
in use. It takes about ten minutes.

You will need Python 3.11 or newer and the `GNU gettext
<https://www.gnu.org/software/gettext/>`_ tools, which Django's
:django-admin:`makemessages` and :django-admin:`compilemessages` commands use. Check
that they are installed:

.. code-block:: console

    $ msgfmt --version

If the command is not found, install gettext (``brew install gettext`` on macOS,
``apt install gettext`` on Debian and Ubuntu).

Create a project
================

Create and activate a virtual environment, then install django-autotranslate, which
also installs Django:

.. code-block:: console

    $ python -m venv .venv
    $ source .venv/bin/activate
    $ pip install django-autotranslate

Create a project and an app:

.. code-block:: console

    $ django-admin startproject mysite .
    $ django-admin startapp greetings

Tell ``django-admin`` which settings to use and where to find the project, so the
commands that follow run against it:

.. code-block:: console

    $ export DJANGO_SETTINGS_MODULE=mysite.settings
    $ export PYTHONPATH=.

Configure the languages
=======================

Open ``mysite/settings.py`` and add ``autotranslate`` and the new app to
:setting:`INSTALLED_APPS`:

.. code-block:: python

    INSTALLED_APPS = [
        ...
        "autotranslate",
        "greetings",
    ]

Then, after :setting:`LANGUAGE_CODE`, list the languages your site supports and tell
Django where to keep its message files:

.. code-block:: python

    LANGUAGES = [
        ("en", "English"),
        ("de", "German"),
        ("es", "Spanish"),
    ]

    LOCALE_PATHS = [BASE_DIR / "locale"]

:setting:`USE_I18N` is already ``True`` in a new project, which django-autotranslate
needs.

Write some messages
===================

Create ``greetings/messages.py`` with three messages marked for translation: one with
a placeholder, one with singular and plural forms, and one with HTML markup:

.. code-block:: python

    from django.utils.translation import gettext as _
    from django.utils.translation import ngettext


    def welcome(name, count):
        return [
            _("Welcome back, %(name)s!") % {"name": name},
            ngettext(
                "You have %(count)d new message.",
                "You have %(count)d new messages.",
                count,
            )
            % {"count": count},
            _('Read the <a href="/help/">help pages</a> to get started.'),
        ]

Create the message files
========================

Create the ``locale`` directory and run :django-admin:`makemessages` for German and
Spanish:

.. code-block:: console

    $ mkdir locale
    $ django-admin makemessages -l de -l es
    processing locale de
    processing locale es

This creates ``locale/de/LC_MESSAGES/django.po`` and
``locale/es/LC_MESSAGES/django.po``. Open the German file. Each message is a
``msgid`` with an empty ``msgstr`` waiting for its translation:

.. code-block:: po

    #: greetings/messages.py:7
    #, python-format
    msgid "Welcome back, %(name)s!"
    msgstr ""

Translate them
==============

Now run ``autotranslate``:

.. code-block:: console

    $ django-admin autotranslate
    Translating /home/you/mysite/locale/de/LC_MESSAGES/django.po into German
    Translating /home/you/mysite/locale/es/LC_MESSAGES/django.po into Spanish

The command found both message files in :setting:`LOCALE_PATHS`, worked out each
file's language from its directory name, and sent the empty messages to the free
Google Translate service.

Open the Spanish file again. The messages are translated, and the placeholders and the
link survived translation unchanged:

.. code-block:: po

    #, python-format
    msgid "Welcome back, %(name)s!"
    msgstr "¡Bienvenido de nuevo, %(name)s!"

    #, python-format
    msgid "You have %(count)d new message."
    msgid_plural "You have %(count)d new messages."
    msgstr[0] "Tienes %(count)d mensaje nuevo."
    msgstr[1] "Tienes %(count)d mensajes nuevos."
    msgstr[2] "Tienes %(count)d mensajes nuevos."

    msgid "Read the <a href=\"/help/\">help pages</a> to get started."
    msgstr "Lea las <a href=\"/help/\">páginas de ayuda</a> para comenzar."

Notice two things:

* **Spanish has three plural forms.** Spanish's plural rules, which Django declares in
  the file's header, have a separate form for millions. ``autotranslate`` fills every
  form the language declares.
* **The tone is inconsistent.** The plural message uses the informal *tienes* (you),
  but the link uses the formal *lea* (read), and the German file uses the formal *Sie*
  throughout. Machine translation does not know your site's voice, so have people who
  speak your languages review the translations, see :ref:`howto-review`.

If the service changes a placeholder or tag in a translation, ``autotranslate``
discards that translation and tells you, so a broken translation never reaches your
site. Django shows the English text for messages that are not translated.

Use the translations
====================

Compile the message files so Django can use them:

.. code-block:: console

    $ django-admin compilemessages

Then try them in the Django shell:

.. code-block:: console

    $ django-admin shell -c "
    from django.utils import translation
    from greetings.messages import welcome
    for language in ['en', 'de', 'es']:
        with translation.override(language):
            print(language, welcome('Ada', 3))
    "
    en ['Welcome back, Ada!', 'You have 3 new messages.', 'Read the <a href="/help/">help pages</a> to get started.']
    de ['Willkommen zurück, Ada!', 'Sie haben 3 neue Nachrichten.', 'Lesen Sie die <a href="/help/">Hilfeseiten</a>, um loszulegen.']
    es ['¡Bienvenido de nuevo, Ada!', 'Tienes 3 mensajes nuevos.', 'Lea las <a href="/help/">páginas de ayuda</a> para comenzar.']

Run it again
============

Run ``autotranslate`` a second time:

.. code-block:: console

    $ django-admin autotranslate

It prints nothing: every message is translated, so there is nothing to send. By
default ``autotranslate`` only translates messages that have no translation, or whose
English text has changed, so running it again is cheap and never overwrites existing
translations.

Next steps
==========

You have translated a Django project. From here:

* Use a paid service for regular use: :ref:`howto-google-cloud` or
  :ref:`howto-amazon`.
* Fit ``autotranslate`` into your workflow: :ref:`howto-update`.
* Learn what happened behind the scenes: :ref:`explanation-how`.

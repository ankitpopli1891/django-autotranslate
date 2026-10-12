.. include:: ../refs.rst

.. _howto-reusable-app:

===================================
Translate a reusable app
===================================

Reusable Django apps ship their own message files in a ``locale`` directory inside the
app, rather than in a project's :setting:`LOCALE_PATHS`.

Create the message files
========================

Run :django-admin:`makemessages` from the app's directory, so it only collects the
app's messages:

.. code-block:: console

    $ cd src/myapp
    $ mkdir -p locale
    $ django-admin makemessages -l de -l fr

Translate them
==============

From a project that has the app in :setting:`INSTALLED_APPS`, translate the app's
``locale`` directory with ``--app`` (``-a``):

.. code-block:: console

    $ django-admin autotranslate --app myapp

or give the directory with ``--path`` (``-p``), which needs no project setup beyond
``autotranslate`` being installed:

.. code-block:: console

    $ django-admin autotranslate --path src/myapp/locale --settings mysite.settings

Both can be given more than once. When either is given, :setting:`LOCALE_PATHS` is
ignored.

Ship the translations
=====================

Compile the message files and include both the ``.po`` and ``.mo`` files in your
package, so installing it gives users the translations:

.. code-block:: console

    $ cd src/myapp && django-admin compilemessages

Make sure your build tool includes them, as ``.mo`` files are often excluded by
``.gitignore`` rules that build tools respect.

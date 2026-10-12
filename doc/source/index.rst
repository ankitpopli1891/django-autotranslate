.. include:: ./refs.rst
.. role:: big

====================
Django AutoTranslate
====================

.. only:: html

    .. image:: https://img.shields.io/badge/License-MIT-blue.svg
        :target: https://opensource.org/licenses/MIT
        :alt: MIT License

    .. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
        :target: https://docs.astral.sh/ruff
        :alt: Ruff

    .. image:: https://badge.fury.io/py/django-autotranslate.svg
        :target: https://pypi.python.org/pypi/django-autotranslate/
        :alt: PyPI Version

    .. image:: https://img.shields.io/pypi/pyversions/django-autotranslate.svg
        :target: https://pypi.python.org/pypi/django-autotranslate/
        :alt: Python Versions

    .. image:: https://img.shields.io/pypi/djversions/django-autotranslate.svg
        :target: https://pypi.org/project/django-autotranslate/
        :alt: Django Versions

    .. image:: https://img.shields.io/pypi/status/django-autotranslate.svg
        :target: https://pypi.python.org/pypi/django-autotranslate
        :alt: Development Status

    .. image:: https://img.shields.io/pypi/types/django-autotranslate.svg
        :target: https://pypi.python.org/pypi/django-autotranslate
        :alt: Typed

    .. image:: https://readthedocs.org/projects/django-autotranslate/badge/?version=latest
        :target: http://django-autotranslate.readthedocs.io/?badge=latest/
        :alt: Documentation Status

    .. image:: https://codecov.io/gh/ankitpopli1891/django-autotranslate/branch/master/graph/badge.svg
        :target: https://codecov.io/gh/ankitpopli1891/django-autotranslate
        :alt: Code Coverage

    .. image:: https://github.com/ankitpopli1891/django-autotranslate/actions/workflows/test.yml/badge.svg?branch=master
        :target: https://github.com/ankitpopli1891/django-autotranslate/actions/workflows/test.yml
        :alt: Test Status

    .. image:: https://github.com/ankitpopli1891/django-autotranslate/actions/workflows/lint.yml/badge.svg
        :target: https://github.com/ankitpopli1891/django-autotranslate/actions/workflows/lint.yml
        :alt: Lint Status

    .. image:: https://img.shields.io/badge/Published%20on-Django%20Packages-0c3c26
        :target: https://djangopackages.org/packages/p/django-autotranslate/
        :alt: Published on Django Packages

django-autotranslate machine translates the message files (``.po``) that Django's
:django-admin:`makemessages` command creates. It sends the messages that need translating
to a machine translation service, protects placeholders like ``%(name)s`` and HTML markup
from being translated, and writes the translations back into your message files.

.. code-block:: console

    $ django-admin makemessages -l de -l es
    $ django-admin autotranslate
    $ django-admin compilemessages

It works with the free Google Translate service out of the box, and with the paid
`Google Cloud Translation <https://cloud.google.com/translate>`_ and
`Amazon Translate <https://aws.amazon.com/translate/>`_ services.

.. note::

    Machine translations are a starting point, not a replacement for human translators.
    Have people who speak your languages review them, see :ref:`howto-review`.

Where to start
==============

:ref:`tutorial`
    New to django-autotranslate? Translate a small Django project from start to finish.

:ref:`howto`
    Step by step guides for common tasks: using a paid service, choosing languages,
    reviewing translations, keeping them up to date and automating them in CI.

:ref:`reference`
    The ``autotranslate`` command, settings, supported languages and the Python API.

:ref:`explanation`
    How the command decides what to translate, how placeholders and markup are
    protected, how language codes are matched and how to choose a service.

.. toctree::
   :maxdepth: 2
   :hidden:

   tutorial
   howto/index
   reference/index
   explanation/index
   changelog

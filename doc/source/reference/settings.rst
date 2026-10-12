.. include:: ../refs.rst

.. _reference-settings:

========
Settings
========

.. setting:: AUTOTRANSLATE_SERVICE

``AUTOTRANSLATE_SERVICE``
=========================

Default: ``"autotranslate.services.GoogleTranslatorService"``

The translation service ``autotranslate`` uses. Either the import path of a service
class:

.. code-block:: python

    AUTOTRANSLATE_SERVICE = "autotranslate.services.GoogleTranslatorService"

or a dictionary with the import path as ``BACKEND`` and ``OPTIONS`` that are passed to
the service as keyword arguments:

.. code-block:: python

    AUTOTRANSLATE_SERVICE = {
        "BACKEND": "autotranslate.services.AmazonTranslateTranslatorService",
        "OPTIONS": {"region_name": "us-east-1"},
    }

The ``--service`` option of ``autotranslate`` overrides the service for a single run.
``OPTIONS`` are only used with the ``BACKEND`` they are configured with.

Service options
---------------

Every service accepts:

``language_map``
    A dictionary mapping Django language codes to the service's language codes. Map a
    language to ``None`` to skip it. Added to, or overriding, the service's built in
    exceptions. See :ref:`explanation-languages`.

:class:`~autotranslate.services.GoogleTranslatorService` (free Google Translate, the
default):

``retries``
    How many times to retry a request that fails because of a network error or because
    Google rejected it. Default ``3``.

``retry_delay``
    Seconds to wait before retrying a network error, doubled for each retry. Default
    ``1.0``.

``rate_limit_delay``
    Seconds to wait before retrying a request Google rejected, usually because of rate
    limiting, doubled for each retry. Default ``30.0``.

:class:`~autotranslate.services.GoogleAPITranslatorService` (Google Cloud Translation,
requires the ``google`` extra):

``api_key``
    Your Google Cloud Translation API key. Required.

``max_segments``
    The most strings sent in one request. The API rejects more than 128. Default
    ``128``.

:class:`~autotranslate.services.AmazonTranslateTranslatorService` (Amazon Translate,
requires the ``amazon`` extra):

Any other options
    Passed to :func:`boto3.client`, for example ``region_name``,
    ``aws_access_key_id`` and ``aws_secret_access_key``. Anything not given is found by
    boto3 as usual: environment variables, ``~/.aws`` configuration or the machine's
    role.

Django settings
===============

``autotranslate`` also uses these Django settings:

:setting:`USE_I18N`
    Must be ``True``.

:setting:`LOCALE_PATHS`
    The directories translated when neither ``--path`` nor ``--app`` is given.

:setting:`LANGUAGES`
    Only used for language names in the command's output. The languages translated are
    the ones you have message files for.

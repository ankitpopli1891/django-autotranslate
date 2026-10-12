.. include:: ../refs.rst

.. _howto-free-google:

===========================================
Work with the free Google Translate service
===========================================

The default service uses Google Translate's free web endpoint. It needs no account, but
it is unofficial and Google limits how much it may be used.

Avoid rate limiting
===================

Google limits the free endpoint by IP address. Translating many languages at once sends
hundreds of requests in a short time, and Google starts rejecting them with
``429 Too Many Requests``. When that happens the service waits and retries, by default
three times starting at 30 seconds and doubling each time. If Google still refuses, the
command stops. Files already translated are saved, and the next run continues with what
is left.

To stay under the limit, translate a few languages at a time:

.. code-block:: console

    $ django-admin autotranslate -l de -l fr -l es
    $ django-admin autotranslate -l ja -l zh_Hans

If you are blocked, wait an hour or so, or run from a different network. Every device
behind the same public IP address is blocked too.

Tune the retries
================

Set the retry behaviour in ``OPTIONS``:

.. code-block:: python

    AUTOTRANSLATE_SERVICE = {
        "BACKEND": "autotranslate.services.GoogleTranslatorService",
        "OPTIONS": {
            "retries": 5,  # retries for network errors and rejected requests
            "retry_delay": 1.0,  # seconds before retrying a network error (doubles)
            "rate_limit_delay": 60.0,  # seconds before retrying a rejected request (doubles)
        },
    }

When to switch
==============

Consider a paid service if you translate regularly, need many languages, or see many
discarded translations: the free service can only send placeholders as tokens in the
text, which it occasionally changes. See :ref:`explanation-services`.

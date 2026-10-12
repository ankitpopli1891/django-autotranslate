.. include:: ../refs.rst

.. _howto-amazon:

=======================
Use Amazon Translate
=======================

`Amazon Translate <https://aws.amazon.com/translate/>`_ is a paid service. It supports
fewer of Django's languages than Google, but has Latin American Spanish and Latin script
Serbian, which Google does not.

Give it access to AWS
=====================

Create AWS credentials that may use Amazon Translate. A dedicated IAM user or role needs
only this policy:

.. code-block:: json

    {
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Action": ["translate:TranslateText", "translate:ListLanguages"],
        "Resource": "*"
      }]
    }

Configure the service
=====================

Install the ``amazon`` extra:

.. code-block:: console

    $ pip install "django-autotranslate[amazon]"

Set :setting:`AUTOTRANSLATE_SERVICE`:

.. code-block:: python

    AUTOTRANSLATE_SERVICE = {
        "BACKEND": "autotranslate.services.AmazonTranslateTranslatorService",
        "OPTIONS": {"region_name": "us-east-1"},
    }

The ``OPTIONS`` are passed to :func:`boto3.client`. Credentials you don't give there are
found the usual boto3 way: the ``AWS_ACCESS_KEY_ID`` and ``AWS_SECRET_ACCESS_KEY``
environment variables, an ``AWS_PROFILE`` from your ``~/.aws`` configuration, or the
role of the machine it runs on. For example:

.. code-block:: console

    $ AWS_PROFILE=translate django-admin autotranslate

Choose a region where Amazon Translate is available.

See also
========

* :ref:`reference-languages` for the languages Amazon supports.
* :ref:`explanation-services` to compare the services.

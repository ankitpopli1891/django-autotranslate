.. include:: ../refs.rst

.. _reference-api:

==========
Python API
==========

.. automodule:: autotranslate

.. _reference-api-services:

Services
========

.. autoclass:: autotranslate.services.TranslatorService
    :members:
    :special-members: __enter__, __exit__

.. autoclass:: autotranslate.services.GoogleTranslatorService
    :members:

.. autoclass:: autotranslate.services.GoogleAPITranslatorService
    :members:

.. autoclass:: autotranslate.services.AmazonTranslateTranslatorService
    :members:

.. autoexception:: autotranslate.services.ServiceUnavailable

Configuration
=============

.. automodule:: autotranslate.config
    :members:

Command
=======

.. autoclass:: autotranslate.management.commands.autotranslate.Command
    :members: get_messages_to_translate, update_translations, need_translate, restore

.. _protect:

Placeholder and markup protection
=================================

.. automodule:: autotranslate.protect.pipeline
    :members:

.. automodule:: autotranslate.protect.parse
    :members: parse, newlines

.. automodule:: autotranslate.protect.segments
    :members:

.. automodule:: autotranslate.protect.guards
    :members: Guard, TokenGuard, HTMLGuard, same_opaques

.. automodule:: autotranslate.protect.repair
    :members: repair, match_edges

.. automodule:: autotranslate.protect.formats
    :members: printf, brace, tokenizers_for

.. automodule:: autotranslate.protect.html
    :members: html, OPAQUE_ELEMENTS, VOID_ELEMENTS

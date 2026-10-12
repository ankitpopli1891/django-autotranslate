"""
Settings for ``just translate``, which machine translates this app's messages using
the paid Google Cloud Translation API.

Set the ``GOOGLE_TRANSLATE_API_KEY`` environment variable to your API key - never
commit the key.
"""

import os

from .settings import *

AUTOTRANSLATE_SERVICE = {
    "BACKEND": "autotranslate.services.GoogleAPITranslatorService",
    "OPTIONS": {
        "api_key": os.environ.get("GOOGLE_TRANSLATE_API_KEY"),
        # the API rejects requests with more than 128 strings
        "max_segments": 128,
    },
}

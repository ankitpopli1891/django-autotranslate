"""
The `compat` module provides support for backwards compatibility with older
versions of Django/Python, and compatibility wrappers around optional packages.
"""
try:
    # Available in Python 3.1+
    import importlib
except ImportError:
    # Will be removed in Django 1.9
    from django.utils import importlib

try:
    import goslate
except ImportError:
    goslate = None

try:
    import googleapiclient
except ImportError:
    googleapiclient = None

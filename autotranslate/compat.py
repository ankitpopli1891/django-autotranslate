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
    import googletrans
except ImportError:
    googletrans  = None
except SyntaxError:
    import sys
    import warnings
    warnings.warn('googletrans disabled due lack support of Python-%s' % (
        sys.version.split()[0][:3]), RuntimeWarning)
    googletrans = None

try:
    import googleapiclient
except ImportError:
    googleapiclient = None

try:
    import boto3
except ImportError:
    boto3 = None

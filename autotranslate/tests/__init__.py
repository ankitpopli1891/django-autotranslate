import pkg_resources
import sys


def _parse_version(v):
   return tuple(map(int, pkg_resources.get_distribution('django').version.split('.')))


# prevent import tests twice in dj16-py26
if sys.version_info[:2] == (2, 6) and \
   _parse_version(pkg_resources.get_distribution('django').version)[:2] == (1, 6):
   pass
else:
   from autotranslate.tests.test_translate_messages import *

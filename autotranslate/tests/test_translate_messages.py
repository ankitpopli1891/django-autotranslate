import os

try:
    # python2.6
    import unittest2 as unittest
except ImportError:
    import unittest

import polib

from autotranslate.management.commands.translate_messages import humanize_placeholders, restore_placeholders, Command


class HumanizeTestCase(unittest.TestCase):
    def test_named_placeholders(self):
        self.assertEqual('foo __item__ bar', humanize_placeholders('foo %(item)s bar'))
        self.assertEqual('foo __item_name__ bar', humanize_placeholders('foo %(item_name)s bar'))

        self.assertEqual('foo % (item)s bar', humanize_placeholders('foo % (item)s bar'))

    def test_positional_placeholders(self):
        self.assertEqual('foo __item__ bar', humanize_placeholders('foo %s bar'))
        self.assertEqual('foo __number__ bar', humanize_placeholders('foo %d bar'))
        self.assertEqual('foo __item__ bar __item__', humanize_placeholders('foo %s bar %s'))
        self.assertEqual('foo __item____item__', humanize_placeholders('foo %s%s'))


class RestoreTestCase(unittest.TestCase):
    def test_restore_placeholders(self):
        self.assertEqual('baz %(item)s zilot',
                         restore_placeholders('foo %(item)s bar', 'baz __over__ zilot'))
        self.assertEqual('baz %(item_name)s zilot',
                         restore_placeholders('foo %(item_name)s bar', 'baz __item_name__ zilot'))
        self.assertEqual('baz %s zilot',
                         restore_placeholders('foo %s bar', 'baz __item__ zilot'))
        self.assertEqual('baz %s%s zilot',
                         restore_placeholders('foo %s%s bar', 'baz __item____item__ zilot'))


class POFileTestCase(unittest.TestCase):
    def setUp(self):
        cmd = Command()
        cmd.set_options(**dict(
                locale='ia',
                set_fuzzy=False,
                skip_translated=False
        ))
        self.cmd = cmd
        self.po = polib.pofile(os.path.join(os.path.dirname(__file__), 'data/django.po'))

    def test_should_read_single(self):
        strings = self.cmd.get_strings_to_translate(self.po)
        self.assertIn('Location', strings)

    def test_should_update_single(self):
        translations = ['XXXX']
        entry = self.po[0]
        self.cmd.update_translations([entry], translations)
        self.assertEqual('XXXX', entry.msgstr)
        self.assertTrue(entry.translated())

    def test_should_read_plural(self):
        strings = self.cmd.get_strings_to_translate(self.po)
        self.assertIn('City', strings)
        self.assertIn('Cities', strings)

    def test_should_update_plural(self):
        translations = ['SINGULAR', 'PLURAL']
        entry = self.po[1]
        self.cmd.update_translations([entry], translations)
        self.assertEqual('', entry.msgstr)
        self.assertEqual('SINGULAR', entry.msgstr_plural[0])
        self.assertEqual(['PLURAL'] * (len(entry.msgstr_plural) - 1),
                         [v for k, v in entry.msgstr_plural.items() if k != 0])
        self.assertTrue(entry.translated())

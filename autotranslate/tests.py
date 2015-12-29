import unittest

from autotranslate.management.commands.translate_messages import humanize_placeholders, restore_placeholders


class TestCase(unittest.TestCase):
    def test1(self):
        self.assertEqual(humanize_placeholders('foo %(item)s bar'), 'foo %(item) bar')
        self.assertEqual(humanize_placeholders('foo %(item_name)s bar'), 'foo %(item_name) bar')

        self.assertEqual(humanize_placeholders('foo % (item)s bar'), 'foo % (item)s bar')
        self.assertEqual(humanize_placeholders('foo %s bar'), 'foo %(item) bar')
        self.assertEqual(humanize_placeholders('foo %d bar'), 'foo %(number) bar')

    def test2(self):
        self.assertEqual(restore_placeholders('foo %(item)s bar', 'baz% ( over ) zilot'), 'baz %(item)s zilot')
        self.assertEqual(restore_placeholders('foo %(item_name)s bar', 'baz% ( item_name ) zilot'),
                         'baz %(item_name)s zilot')
        self.assertEqual(restore_placeholders('foo %s bar', 'baz% ( item ) zilot'), 'baz %s zilot')

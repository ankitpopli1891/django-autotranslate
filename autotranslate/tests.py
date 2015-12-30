import unittest

from autotranslate.management.commands.translate_messages import humanize_placeholders, restore_placeholders


class HumanizeTestCase(unittest.TestCase):
    def test_named_placeholders(self):
        self.assertEqual(humanize_placeholders('foo %(item)s bar'), 'foo __item__ bar')
        self.assertEqual(humanize_placeholders('foo %(item_name)s bar'), 'foo __item_name__ bar')

        self.assertEqual(humanize_placeholders('foo % (item)s bar'), 'foo % (item)s bar')

    def test_positional_placeholders(self):
        self.assertEqual(humanize_placeholders('foo %s bar'), 'foo __item__ bar')
        self.assertEqual(humanize_placeholders('foo %d bar'), 'foo __number__ bar')
        self.assertEqual(humanize_placeholders('foo %s bar %s'), 'foo __item__ bar __item__')
        self.assertEqual(humanize_placeholders('foo %s%s'), 'foo __item____item__')


class RestoreTestCase(unittest.TestCase):
    def test_restore_placeholders(self):
        self.assertEqual(restore_placeholders('foo %(item)s bar', 'baz __over__ zilot'),
                         'baz %(item)s zilot')
        self.assertEqual(restore_placeholders('foo %(item_name)s bar', 'baz __item_name__ zilot'),
                         'baz %(item_name)s zilot')
        self.assertEqual(restore_placeholders('foo %s bar', 'baz __item__ zilot'),
                         'baz %s zilot')
        self.assertEqual(restore_placeholders('foo %s%s bar', 'baz __item____item__ zilot'),
                         'baz %s%s zilot')

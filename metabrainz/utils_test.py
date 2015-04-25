from unittest import TestCase
from metabrainz import utils
from datetime import datetime


class UtilsTestCase(TestCase):

    def test_reformat_datetime(self):
        d = datetime(2000, 1, 11, 12, 30)
        self.assertEqual(utils.reformat_datetime(d), '01/11/00 12:30:00 ')

    def test_generate_string(self):
        length = 42
        str_1 = utils.generate_string(length)
        str_2 = utils.generate_string(length)

        self.assertEqual(len(str_1), length)
        self.assertEqual(len(str_2), length)
        self.assertNotEqual(str_1, str_2)  # Generated strings shouldn't be the same

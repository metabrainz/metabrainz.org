import json
from unittest import TestCase
from metabrainz import utils
from metabrainz.utils import react_props
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


class ReactPropsTestCase(TestCase):
    """Props are embedded raw in a <script> block, so they must not be able to
    close it. Descriptions echoed back by authlib can contain any character an
    OAuth client puts in the query string."""

    def test_script_tag_cannot_break_out(self):
        payload = "</script><img src=x onerror=alert(1)>"
        escaped = react_props(json.dumps({"description": payload}))
        self.assertNotIn("<", escaped)
        self.assertNotIn(">", escaped)
        self.assertNotIn("&", escaped)

    def test_value_survives_the_round_trip(self):
        props = {"description": "</script> & <b>a</b> \u2028 \u2029"}
        self.assertEqual(json.loads(react_props(json.dumps(props))), props)

    def test_missing_props_render_an_empty_object(self):
        self.assertEqual(react_props(None), "{}")
        self.assertEqual(react_props(""), "{}")

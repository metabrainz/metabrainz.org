from unittest import TestCase

from wtforms import ValidationError

from metabrainz.user import username

ZERO_WIDTH_SPACE = chr(0x200B)
BOM = chr(0xFEFF)
NONCHARACTER = chr(0xFFFE)
NONCHARACTER_PLANE1 = chr(0x1FFFE)
BRAILLE_BLANK = chr(0x2800)
HANGUL_FILLER = chr(0x3164)
TAG_LATIN_A = chr(0xE0041)
COMBINING_ACUTE = chr(0x0301)
PRECOMPOSED_E_ACUTE = chr(0x00E9)
LEFT_TO_RIGHT_MARK = chr(0x200E)
RIGHT_TO_LEFT_MARK = chr(0x200F)
# Arabic name "Ali" (ayn, lam, ya), a right-to-left string.
ARABIC_NAME = chr(0x0639) + chr(0x0644) + chr(0x064A)


class SanitizeUsernameTestCase(TestCase):

    def test_plain_username_unchanged(self):
        self.assertEqual(username.sanitize_username("normal_user"), "normal_user")

    def test_empty_input(self):
        self.assertEqual(username.sanitize_username(None), "")
        self.assertEqual(username.sanitize_username(""), "")

    def test_collapses_whitespace(self):
        self.assertEqual(username.sanitize_username("John\t\t  Doe"), "John Doe")

    def test_removes_zero_width_space(self):
        self.assertEqual(username.sanitize_username("John" + ZERO_WIDTH_SPACE + "Doe"), "JohnDoe")

    def test_removes_control_characters(self):
        self.assertEqual(username.sanitize_username("Jo\x00hn"), "John")

    def test_removes_bom(self):
        self.assertEqual(username.sanitize_username(BOM + "John"), "John")

    def test_removes_noncharacters(self):
        self.assertEqual(username.sanitize_username("Jo" + NONCHARACTER + "hn"), "John")
        self.assertEqual(username.sanitize_username("Jo" + NONCHARACTER_PLANE1 + "hn"), "John")

    def test_removes_invisible_characters(self):
        self.assertEqual(
            username.sanitize_username("Jo" + BRAILLE_BLANK + HANGUL_FILLER + "hn"),
            "John",
        )

    def test_all_invisible_becomes_empty(self):
        self.assertEqual(username.sanitize_username(BRAILLE_BLANK + HANGUL_FILLER), "")

    def test_removes_tag_characters(self):
        self.assertEqual(username.sanitize_username("John" + TAG_LATIN_A), "John")

    def test_nfc_normalization(self):
        # "e" + combining acute accent should normalize to a single precomposed
        # e-acute (U+00E9).
        self.assertEqual(
            username.sanitize_username("Jos" + "e" + COMBINING_ACUTE),
            "Jos" + PRECOMPOSED_E_ACUTE,
        )

    def test_strips_direction_marks_for_ltr(self):
        self.assertEqual(
            username.sanitize_username("John" + LEFT_TO_RIGHT_MARK + "Doe"),
            "JohnDoe",
        )

    def test_keeps_text_with_rtl_characters(self):
        # An Arabic name keeps its letters; the trailing RLM between a strong
        # character and the end of the string is removed.
        self.assertEqual(
            username.sanitize_username(ARABIC_NAME + RIGHT_TO_LEFT_MARK),
            ARABIC_NAME,
        )


class _Field:
    def __init__(self, data):
        self.data = data


class ValidateUsernameTestCase(TestCase):

    def _validate(self, value):
        username.validate_username(None, _Field(value))

    def test_valid_username_passes(self):
        self._validate("normal_user")  # should not raise

    def test_empty_is_skipped(self):
        # DataRequired is responsible for empty values; this validator skips them.
        self._validate("")
        self._validate(None)

    def test_invisible_characters_rejected(self):
        with self.assertRaises(ValidationError):
            self._validate("John" + ZERO_WIDTH_SPACE + "Doe")

    def test_only_invisible_characters_rejected(self):
        with self.assertRaises(ValidationError):
            self._validate(BRAILLE_BLANK + HANGUL_FILLER)

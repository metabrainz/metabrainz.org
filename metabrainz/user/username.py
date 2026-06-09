"""Username sanitization and validation helpers.

This is a Python port of the relevant parts of MusicBrainz Server's
``MusicBrainz::Server::Data::Utils`` module (``sanitize_username`` and the
helpers it relies on). Keeping the behaviour in sync ensures usernames created
through MetaBrainz match what MusicBrainz Server expects.

The character classes below are built from explicit Unicode code points (rather
than literal characters or string escapes) so the source stays plain ASCII and
every code point is easy to read and audit.
"""
import re
import unicodedata

from flask_babel import gettext
from wtforms import ValidationError


def _char_class(*items):
    """Build a regex character-class body from code points and (lo, hi) ranges."""
    parts = []
    for item in items:
        if isinstance(item, tuple):
            lo, hi = item
            parts.append(f"{chr(lo)}-{chr(hi)}")
        else:
            parts.append(chr(item))
    return "".join(parts)


LEFT_TO_RIGHT_MARK = chr(0x200E)
RIGHT_TO_LEFT_MARK = chr(0x200F)
_DIRECTION_MARKS = (LEFT_TO_RIGHT_MARK, RIGHT_TO_LEFT_MARK)

# Unicode noncharacters: https://www.unicode.org/faq/private_use.html#nonchar4
# U+FDD0-U+FDEF, U+FFFE/U+FFFF and the last two code points of every plane.
_NONCHARACTERS = [(0xFDD0, 0xFDEF), 0xFFFE, 0xFFFF]
for _plane in range(1, 17):
    _NONCHARACTERS += [(_plane << 16) | 0xFFFE, (_plane << 16) | 0xFFFF]

# XML-invalid characters (e.g. surrogates) are anything outside these ranges.
_INVALID_CHARS_RE = re.compile(
    "[^" + _char_class(
        0x0009, 0x000A, 0x000D,
        (0x0020, 0xD7FF),
        (0xE000, 0xFFFD),
        (0x10000, 0x10FFFF),
    ) + "]"
)

# Other undesirable characters: the BOM (U+FEFF), the supplementary private use
# areas (U+F0000-U+FFFFF, U+100000-U+10FFFF) and the Unicode noncharacters.
_UNDESIRABLE_CHARS_RE = re.compile(
    "[" + _char_class(
        0xFEFF,
        (0xF0000, 0xFFFFF),
        (0x100000, 0x10FFFF),
        *_NONCHARACTERS,
    ) + "]"
)

# Line-formatting characters: zero width space (U+200B), soft hyphen (U+00AD)
# and control chars (category Cc, i.e. U+0000-U+001F and U+007F-U+009F).
_LINEFORMATTING_CHARS_RE = re.compile(
    "[" + _char_class(0x200B, 0x00AD, (0x0000, 0x001F), (0x007F, 0x009F)) + "]"
)

# Invisible characters that render as blank but are not whitespace: braille
# pattern blank (U+2800), Hangul filler (U+3164), halfwidth Hangul filler
# (U+FFA0), Hangul jungseong filler (U+1160) and Hangul choseong filler (U+115F).
_INVISIBLE_CHARS_RE = re.compile(
    "[" + _char_class(0x2800, 0x3164, 0xFFA0, 0x1160, 0x115F) + "]"
)

# Tag characters: https://en.wikipedia.org/wiki/Tags_(Unicode_block)
_TAG_CHARS_RE = re.compile("[" + _char_class((0xE0000, 0xE007F)) + "]")


def non_empty(value):
    return value is not None and value != ""


def collapse_whitespace(value):
    # Replace all whitespace with U+0020, then compress runs of whitespace.
    value = re.sub(r"\s", " ", value)
    value = re.sub(r"\s{2,}", " ", value)
    return value


def remove_invalid_characters(value):
    value = _INVALID_CHARS_RE.sub("", value)
    value = _UNDESIRABLE_CHARS_RE.sub("", value)
    return value


def remove_lineformatting_characters(value):
    return _LINEFORMATTING_CHARS_RE.sub("", value)


def remove_invisible_characters(value):
    value = remove_lineformatting_characters(value)
    return _INVISIBLE_CHARS_RE.sub("", value)


def remove_tag_characters(value):
    return _TAG_CHARS_RE.sub("", value)


def _is_strong(char):
    return unicodedata.bidirectional(char) in ("L", "R", "AL")


def _is_rtl(char):
    return unicodedata.bidirectional(char) in ("R", "AL")


def remove_direction_marks(value):
    # Remove LRM/RLM runs sitting between two strong characters (the start and
    # end of the string are treated like strong characters too).
    result = []
    length = len(value)
    i = 0
    while i < length:
        char = value[i]
        if char in _DIRECTION_MARKS:
            j = i
            while j < length and value[j] in _DIRECTION_MARKS:
                j += 1
            before_strong = i == 0 or _is_strong(value[i - 1])
            after_strong = j == length or _is_strong(value[j])
            if not (before_strong and after_strong):
                result.append(value[i:j])
            i = j
        else:
            result.append(char)
            i += 1
    value = "".join(result)

    # Remove the remaining LRM/RLM marks if the string has no RTL characters.
    # The test must be done on the stripped string because RLM is RTL itself.
    stripped = value.replace(LEFT_TO_RIGHT_MARK, "").replace(RIGHT_TO_LEFT_MARK, "")
    if not any(_is_rtl(char) for char in stripped):
        return stripped
    return value


def sanitize(value):
    if not non_empty(value):
        return ""

    value = unicodedata.normalize("NFC", value)
    # Before removing invalid characters, convert space control characters into
    # U+0020 (or else they'll be removed).
    value = collapse_whitespace(value)
    value = remove_invalid_characters(value)
    value = remove_lineformatting_characters(value)
    value = remove_direction_marks(value)
    # Collapse spaces again, since characters may have been removed.
    value = collapse_whitespace(value)
    return value


def sanitize_username(value):
    if not non_empty(value):
        return ""

    value = sanitize(value)
    value = remove_invisible_characters(value)
    value = remove_tag_characters(value)
    return value


def validate_username(form, field):
    """WTForms validator rejecting usernames with invalid/invisible characters."""
    if not non_empty(field.data):
        return

    sanitized = sanitize_username(field.data)
    if not sanitized:
        raise ValidationError(gettext("Username is not valid."))
    if sanitized != field.data:
        raise ValidationError(
            gettext("Username contains invalid or invisible characters.")
        )

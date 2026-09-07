import json
from urllib.parse import urlparse, parse_qsl, urlunparse, urlencode

import random
import string

from flask import request
from markupsafe import Markup

from metabrainz.i18n import get_locale


def reformat_datetime(value, format='%x %X %Z'):
    return value.strftime(format)


def generate_string(length):
    """Generates random string with a specified length."""
    return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits)
                   for _ in range(length))


def build_url(base, additional_params=None):
    url = urlparse(base)
    query_params = {}
    query_params.update(parse_qsl(url.query, True))
    if additional_params is not None:
        query_params.update(additional_params)
        for key, val in additional_params.items():
            if val is None:
                query_params.pop(key)

    return urlunparse(
        (url.scheme, url.netloc, url.path, url.params,
         urlencode(query_params), url.fragment)
    )


def get_int_query_param(key: str, default: int):
    """ Get an integer query parameter from the current request
        Args:
            key: the key whose value to retrieve
            default: the value to return in case the param is missing
             or not a valid integer
        Returns:
            the value of query param if its available and a valid integer,
             else the default value
    """
    try:
        return int(request.args.get(key, default=default))
    except ValueError:
        return default


def get_global_props():
    return json.dumps({"locale": get_locale()})


# Characters that must never appear raw inside a <script> element. In
# particular "<" can begin the "</script" that ends the block early, after
# which the rest of the value is parsed as HTML: an error description echoing
# an attacker-controlled query parameter is enough to inject a script tag.
# Escaping them as JSON \u sequences leaves the value unchanged after
# JSON.parse(). U+2028/U+2029 are escaped too, as they are line terminators
# in JavaScript source but legal raw in JSON.
_SCRIPT_UNSAFE_CHARACTERS = {
    "<": "\\u003c",
    ">": "\\u003e",
    "&": "\\u0026",
    "\u2028": "\\u2028",
    "\u2029": "\\u2029",
}


def react_props(value):
    """Escape an already serialised JSON string for embedding in a script tag."""
    if not value:
        return Markup("{}")
    value = str(value)
    for character, escaped in _SCRIPT_UNSAFE_CHARACTERS.items():
        value = value.replace(character, escaped)
    return Markup(value)

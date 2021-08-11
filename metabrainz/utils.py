from urllib.parse import urlparse, parse_qsl, urlunparse, urlencode

import random
import string
import subprocess

from flask import request


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

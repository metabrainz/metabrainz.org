import urllib.parse

import random
import string
import subprocess


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

def parameterize(value, key):
    """
    Add a new parameter to the current url.
    Taken from: http://stackoverflow.com/a/2506477
    """
    url_parts = list(urllib.parse.urlparse(request.url))

    query = urllib.parse.parse_qs(url_parts[4])
    query[key] = value
    url_parts[4] = urllib.parse.urlencode(query, doseq=True)

    return urllib.parse.urlunparse(url_parts)

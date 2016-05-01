import urlparse
import urllib
import string
import random


def reformat_datetime(value, format='%x %X %Z'):
    return value.strftime(format)


def generate_string(length):
    """Generates random string with a specified length."""
    return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits)
                   for _ in range(length))


def build_url(base, additional_params=None):
    url = urlparse.urlparse(base)
    query_params = {}
    query_params.update(urlparse.parse_qsl(url.query, True))
    if additional_params is not None:
        query_params.update(additional_params)
        for key, val in additional_params.iteritems():
            if val is None:
                query_params.pop(key)

    return urlparse.urlunparse(
        (url.scheme, url.netloc, url.path, url.params,
         urllib.urlencode(query_params), url.fragment))

import string
import random


def reformat_datetime(value, format='%x %X %Z'):
    return value.strftime(format)


def generate_string(length):
    """Generates random string with a specified length."""
    return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits)
                   for _ in range(length))

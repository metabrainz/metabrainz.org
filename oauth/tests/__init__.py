from contextlib import contextmanager

from flask import g


@contextmanager
def login_user(user):
    try:
        g._login_user = user
        yield user
    finally:
        del g._login_user

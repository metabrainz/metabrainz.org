from flask import session

_SESSION_KEY = 'metabrainz'


def persist_data(**kwargs):
    """Save data in a session."""
    if _SESSION_KEY not in session:
        session[_SESSION_KEY] = dict()
    session[_SESSION_KEY].update(**kwargs)
    session.modified = True


def fetch_data(key, default=None):
    """Fetch data from a session."""
    if _SESSION_KEY not in session:
        return None
    else:
        return session[_SESSION_KEY].get(key, default)


def clear():
    session.clear()

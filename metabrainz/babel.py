from flask_babel import Babel

from metabrainz.i18n import get_locale


def init_app(app):
    Babel(app, locale_selector=get_locale)

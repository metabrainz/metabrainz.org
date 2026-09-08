"""Translatable descriptions for the OAuth scopes seeded into oauth.scope.

The descriptions are stored in the database (see
admin/sql/oauth/create_tables.sql), so string extraction cannot find them
there. Mirroring them here lets the consent screen -- where the user decides
what access to hand over, and so the one page that most needs to be understood
-- be shown in their own language. A scope with no entry here falls back to the
description held in the database.
"""
from flask_babel import gettext

from metabrainz.i18n import N_

SCOPE_DESCRIPTIONS = {
    "profile": N_("View your public account information"),
    "email": N_("View your email address"),
    "musicbrainz:tag": N_("View and modify your private tags"),
    "musicbrainz:rating": N_("View and modify your private ratings"),
    "musicbrainz:collection": N_("View and modify your private collections"),
    "musicbrainz:submit_isrc": N_("Submit new ISRCs to the database"),
    "musicbrainz:submit_barcode": N_("Submit new barcodes to the database"),
    "openid": N_("Sign you in and view your unique user id"),
    "listenbrainz:submit-listens": N_("Submit listens to ListenBrainz."),
    "critiquebrainz:review": N_("Create and modify CritiqueBrainz reviews."),
    "critiquebrainz:vote": N_("Submit and delete votes on CritiqueBrainz reviews."),
    "critiquebrainz:profile": N_("Modify profile info and delete profile on CritiqueBrainz."),
}


def scope_description(scope):
    """Return the translated description of a scope for display to a user."""
    description = SCOPE_DESCRIPTIONS.get(scope.name)
    return gettext(description) if description else scope.description

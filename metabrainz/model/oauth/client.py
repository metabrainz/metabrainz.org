from enum import IntFlag

from authlib.oauth2.rfc6749 import ClientMixin
from sqlalchemy import Column, Text, Integer, ARRAY, Identity, DateTime, func, CheckConstraint

from metabrainz.model import db


class OAuth2ClientPrivilege(IntFlag):
    """ Privileges an OAuth2 client may be granted.

    Stored as a bitmap in the ``privileges`` column and tested with bitwise
    operations. Values are powers of two and must never be reused/renumbered
    once assigned, as existing rows encode them positionally.
    """
    REMEMBER_ME = 1 << 0
    CLIENT_CREDENTIALS = 1 << 1
    REGISTRATION_REQUEST = 1 << 2


# Human-readable labels shown in the admin UI and to application owners.
OAUTH2_CLIENT_PRIVILEGE_LABELS = {
    OAuth2ClientPrivilege.REMEMBER_ME: "Remember me",
    OAuth2ClientPrivilege.CLIENT_CREDENTIALS: "Client credentials grant",
    OAuth2ClientPrivilege.REGISTRATION_REQUEST: "Registration requests",
}


class OAuth2Client(db.Model, ClientMixin):

    __tablename__ = "client"
    __table_args__ = (
        # a privilege bitmap is unsigned; guard against negative values that
        # would otherwise satisfy every bitwise privilege check
        CheckConstraint("privileges >= 0", name="client_privileges_non_negative"),
        {"schema": "oauth"},
    )

    id = Column(Integer, Identity(), primary_key=True)
    client_id = Column(Text, nullable=False)
    client_secret = Column(Text)
    # no FK to user table because user data lives in MB db
    owner_id = Column(Integer, nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    website = Column(Text)
    redirect_uris = Column(ARRAY(Text), nullable=False)
    client_id_issued_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    # bitmap of OAuth2ClientPrivilege flags granted to this client
    privileges = Column(Integer, nullable=False, server_default="0")

    def has_privilege(self, privilege: OAuth2ClientPrivilege) -> bool:
        """ Check whether this client has been granted the given privilege. """
        return bool(self.privileges & privilege)

    def privilege_labels(self) -> list[str]:
        """ Human-readable labels for the privileges granted to this client. """
        granted = OAuth2ClientPrivilege(self.privileges)
        return [
            label
            for privilege, label in OAUTH2_CLIENT_PRIVILEGE_LABELS.items()
            if privilege in granted
        ]

    def get_client_id(self):
        return self.client_id

    def get_default_redirect_uri(self):
        return None

    def get_allowed_scope(self, scope):
        return scope

    def check_redirect_uri(self, redirect_uri):
        return redirect_uri in self.redirect_uris

    def has_client_secret(self):
        return bool(self.client_secret)

    def check_client_secret(self, client_secret):
        return self.client_secret == client_secret

    def check_endpoint_auth_method(self, method, endpoint):
        return True

    def check_response_type(self, response_type):
        return True

    def check_grant_type(self, grant_type):
        if grant_type == "client_credentials":
            return self.has_privilege(OAuth2ClientPrivilege.CLIENT_CREDENTIALS)
        return True

    def check_already_approved(self, user_id, requested_scopes):
        """ Check if the user has previously approved all the scopes for a given client """
        from metabrainz.model.oauth.access_token import OAuth2AccessToken

        requested_scopes = {s.name for s in requested_scopes}
        tokens = db.session.query(OAuth2AccessToken).filter_by(client_id=self.id, user_id=user_id, revoked=False).all()
        for token in tokens:
            existing_scopes = {s.name for s in token.scopes}
            if existing_scopes.issuperset(requested_scopes):
                return True
        return False

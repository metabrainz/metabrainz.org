from metabrainz.new_oauth.models import db


class OAuth2User(db.Model):
    __tablename__ = "user"
    __table_args__ = {
        "schema": "oauth"
    }

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)

    def __str__(self):
        return self.name

    def get_user_id(self):
        return self.id

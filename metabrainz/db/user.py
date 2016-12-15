from metabrainz import db
from metabrainz.model.user import User
import sqlalchemy


def update(user_id, **kwargs):
    user = User.get(id=user_id)
    if not user:
        raise ValueError("Can't find user with a specified ID (%s)" % user_id)

    multiparams = {
        "id": user_id,
        "musicbrainz_id": kwargs.pop("musicbrainz_id", user.musicbrainz_id),
        "contact_name": kwargs.pop("contact_name", user.contact_name),
        "contact_email": kwargs.pop("contact_email", user.contact_email),
        "state": kwargs.pop("state", user.state),
        "is_commercial": kwargs.pop("is_commercial", user.is_commercial),
        "org_name": kwargs.pop("org_name", user.org_name),
        "org_desc": kwargs.pop("org_desc", user.org_desc),
        "api_url": kwargs.pop("api_url", user.api_url),
        "address_street": kwargs.pop("address_street", user.address_street),
        "address_city": kwargs.pop("address_city", user.address_city),
        "address_state": kwargs.pop("address_state", user.address_state),
        "address_postcode": kwargs.pop("address_postcode", user.address_postcode),
        "address_country": kwargs.pop("address_country", user.address_country),
        "tier_id": kwargs.pop("tier_id", user.tier_id),
        "amount_pledged": kwargs.pop("amount_pledged", user.amount_pledged),
        "featured": kwargs.pop("featured", user.featured),
        "website_url": kwargs.pop("website_url", user.website_url),
        "logo_filename": kwargs.pop("logo_filename", user.logo_filename),
        "org_logo_url": kwargs.pop("org_logo_url", user.org_logo_url),
        "data_usage_desc": kwargs.pop("data_usage_desc", user.data_usage_desc),
        "good_standing": kwargs.pop("good_standing", user.good_standing),
        "in_deadbeat_club": kwargs.pop("in_deadbeat_club", user.in_deadbeat_club),
    }
    if kwargs:
        raise TypeError("Unexpected **kwargs: %r" % kwargs)

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE "user"
               SET musicbrainz_id = :musicbrainz_id,
                   contact_name = :contact_name,
                   contact_email = :contact_email,
                   state = :state,
                   is_commercial = :is_commercial,
                   org_name = :org_name,
                   org_desc = :org_desc,
                   api_url = :api_url,
                   address_street = :address_street,
                   address_city = :address_city,
                   address_state = :address_state,
                   address_postcode = :address_postcode,
                   address_country = :address_country,
                   tier_id = :tier_id,
                   amount_pledged = :amount_pledged,
                   featured = :featured,
                   website_url = :website_url,
                   logo_filename = :logo_filename,
                   org_logo_url = :org_logo_url,
                   data_usage_desc = :data_usage_desc,
                   good_standing = :good_standing,
                   in_deadbeat_club = :in_deadbeat_club
             WHERE id = :id
        """), multiparams)

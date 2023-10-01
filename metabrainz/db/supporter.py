from metabrainz import db
from metabrainz.model.supporter import Supporter
import sqlalchemy


def update(supporter_id, **kwargs):
    supporter = Supporter.get(id=supporter_id)
    if not supporter:
        raise ValueError("Can't find supporter with a specified ID (%s)" % supporter_id)

    multiparams = {
        "id": supporter_id,
        "contact_name": kwargs.pop("contact_name", supporter.contact_name),
        "contact_email": kwargs.pop("contact_email", supporter.contact_email),
        "state": kwargs.pop("state", supporter.state),
        "is_commercial": kwargs.pop("is_commercial", supporter.is_commercial),
        "org_name": kwargs.pop("org_name", supporter.org_name),
        "org_desc": kwargs.pop("org_desc", supporter.org_desc),
        "api_url": kwargs.pop("api_url", supporter.api_url),
        "address_street": kwargs.pop("address_street", supporter.address_street),
        "address_city": kwargs.pop("address_city", supporter.address_city),
        "address_state": kwargs.pop("address_state", supporter.address_state),
        "address_postcode": kwargs.pop("address_postcode", supporter.address_postcode),
        "address_country": kwargs.pop("address_country", supporter.address_country),
        "tier_id": kwargs.pop("tier_id", supporter.tier_id),
        "amount_pledged": kwargs.pop("amount_pledged", supporter.amount_pledged),
        "featured": kwargs.pop("featured", supporter.featured),
        "website_url": kwargs.pop("website_url", supporter.website_url),
        "logo_filename": kwargs.pop("logo_filename", supporter.logo_filename),
        "org_logo_url": kwargs.pop("org_logo_url", supporter.org_logo_url),
        "data_usage_desc": kwargs.pop("data_usage_desc", supporter.data_usage_desc),
        "good_standing": kwargs.pop("good_standing", supporter.good_standing),
        "in_deadbeat_club": kwargs.pop("in_deadbeat_club", supporter.in_deadbeat_club),
    }
    if kwargs:
        raise TypeError("Unexpected **kwargs: %r" % kwargs)

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE supporter
               SET contact_name = :contact_name,
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

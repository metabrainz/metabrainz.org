from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, BooleanField, SelectField, TextAreaField
from wtforms.fields import EmailField, URLField, DecimalField
from metabrainz.model import supporter
from metabrainz.db import tier as db_tier
from flask_uploads import UploadSet, IMAGES

import os.path

# ensure that the path is kept in sync with the volume mount path for production in docker-server-configs
LOGO_STORAGE_DIR = os.path.join("/static", "img", "logos", "supporters")
if not os.path.exists(LOGO_STORAGE_DIR):
    os.makedirs(LOGO_STORAGE_DIR)

LOGO_UPLOAD_SET_NAME = "supporterlogo"
LOGO_UPLOAD_SET = UploadSet(
    name=LOGO_UPLOAD_SET_NAME,
    extensions=IMAGES,
    default_dest=lambda app: LOGO_STORAGE_DIR,
)


class SupporterEditForm(FlaskForm):
    # General info
    contact_name = StringField("Name")
    contact_email = EmailField("Email")

    # Data access
    state = SelectField("State", choices=[
        (supporter.STATE_ACTIVE, "Active"),
        (supporter.STATE_PENDING, "Pending"),
        (supporter.STATE_WAITING, "Waiting"),
        (supporter.STATE_REJECTED, "Rejected"),
        (supporter.STATE_LIMITED, "Limited"),
    ])

    # Commercial info
    is_commercial = BooleanField("This is a commercial supporter")
    org_name = StringField("Organization name")
    org_desc = TextAreaField("Description")
    api_url = URLField("URL of the organization's API (if exists)")
    address_street = StringField("Street")
    address_city = StringField("City")
    address_state = StringField("State / Province")
    address_postcode = StringField("Postcode")
    address_country = StringField("Country")

    # Financial info
    tier = SelectField("Tier", default="None")
    amount_pledged = DecimalField("Amount pledged", default=0)

    # Promotion
    featured = BooleanField("Featured supporter")
    website_url = URLField("Website URL")
    logo_url = URLField("Logo image URL (legacy)")
    logo = FileField("Logo image", validators=[
        FileAllowed(LOGO_UPLOAD_SET, "Logo must be an image!")
    ])
    usage_desc = TextAreaField("Data usage description")
    good_standing = BooleanField("Good standing")
    in_deadbeat_club = BooleanField("In the Deadbeat Club(TM)")

    def __init__(self, defaults=None, **kwargs):
        for key, val in defaults.items():
            kwargs.setdefault(key, val)
        FlaskForm.__init__(self, **kwargs)
        self.tier.choices = [(str(t["id"]), t["name"]) for t in db_tier.get_all()]
        self.tier.choices.insert(0, ("None", "None"))

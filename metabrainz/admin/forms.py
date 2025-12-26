from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, BooleanField, SelectField, TextAreaField
from wtforms.fields import EmailField, URLField, DecimalField
from wtforms.validators import DataRequired, Length
from metabrainz.model import supporter
from metabrainz.db import tier as db_tier
from flask_uploads import UploadSet, IMAGES

import os.path


def get_logo_storage_dir(app):
    # ensure that the path is kept in sync with the volume mount path for production in docker-server-configs
    logo_storage_dir = os.path.join(app.config["STATIC_RESOURCES_DIR"], "img", "logos", "supporters")
    if not os.path.exists(logo_storage_dir):
        os.makedirs(logo_storage_dir)
    return logo_storage_dir


LOGO_UPLOAD_SET_NAME = "supporterlogo"
LOGO_UPLOAD_SET = UploadSet(
    name=LOGO_UPLOAD_SET_NAME,
    extensions=IMAGES,
    default_dest=get_logo_storage_dir,
)


class SupporterEditForm(FlaskForm):
    # General info
    username = StringField("Username")
    email = EmailField("Email")

    contact_name = StringField("Name")

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


class VerifyEmailForm(FlaskForm):
    """Form for manually verifying a user's email address."""
    pass


class EditUsernameForm(FlaskForm):
    """Form for editing a user's username."""
    username = StringField(
        "New Username",
        validators=[
            DataRequired(message="Username cannot be empty"),
            Length(min=1, max=255, message="Username must be between 1 and 255 characters")
        ]
    )


class ModerateUserForm(FlaskForm):
    """Form for moderating a user (block/unblock/comment)."""
    action = SelectField(
        "Action",
        choices=[
            ("", "Select an action"),
            ("block", "Block User"),
            ("unblock", "Unblock User"),
            ("comment", "Add Note"),
        ],
        validators=[DataRequired(message="Please select an action")]
    )
    reason = TextAreaField(
        "Reason / Notes",
        validators=[DataRequired(message="A reason is required")]
    )


class DeleteUserForm(FlaskForm):
    """Form for deleting a user with confirmation."""
    reason = TextAreaField(
        "Reason for deletion",
        validators=[DataRequired(message="A reason is required")]
    )
    confirm = BooleanField(
        "I confirm that I want to permanently delete this user",
        validators=[DataRequired(message="You must confirm the deletion")]
    )


class DeleteSupporterForm(FlaskForm):
    """Form for deleting a supporter and their associated user account."""
    reason = TextAreaField(
        "Reason for deletion",
        validators=[DataRequired(message="A reason is required")]
    )
    confirm = BooleanField(
        "I confirm that I want to permanently delete this supporter and their user account",
        validators=[DataRequired(message="You must confirm the deletion")]
    )


class RetryDeliveryForm(FlaskForm):
    """Form for retrying a failed webhook delivery."""
    pass


class DeleteForm(FlaskForm):
    """Simple form for CSRF protection on delete operations."""
    pass

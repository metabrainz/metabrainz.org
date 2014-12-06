from metabrainz.model import db
from flask_admin.contrib.sqla import ModelView


class Organization(db.Model):
    __tablename__ = 'organization'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.Unicode, nullable=False)
    logo_url = db.Column(db.Unicode)
    website_url = db.Column(db.Unicode)
    api_url = db.Column(db.Unicode)
    description = db.Column(db.Unicode)  # How organization uses MetaBrainz projects
    good_standing = db.Column(db.Boolean, nullable=False, default=True)

    contact_name = db.Column(db.Unicode, nullable=False)
    email = db.Column(db.Unicode, nullable=False)

    # Address
    address_street = db.Column(db.Unicode)
    address_city = db.Column(db.Unicode)
    address_state = db.Column(db.Unicode)
    address_postcode = db.Column(db.Unicode)
    address_country = db.Column(db.Unicode)

    tier_id = db.Column(db.Integer, db.ForeignKey('tier.id'))

    donations = db.relationship('Donation', backref='organization')

    def __unicode__(self):
        return self.name


class OrganizationAdminView(ModelView):
    column_labels = dict(
        id='ID',
        logo_url='Logo URL',
        website_url='Homepage URL',
        api_url='API page URL',
        contact_name='Contact name',
        email='Email',
        address_street='Street',
        address_city='City',
        address_state='State',
        address_postcode='Postal code',
        address_country='Country',
    )
    column_descriptions = dict(
        description='How organization uses MetaBrainz projects',
    )
    column_list = ('name', 'tier', 'good_standing',)
    form_columns = (
        'name', 'tier', 'good_standing', 'logo_url', 'website_url', 'api_url',
        'contact_name', 'email', 'address_street', 'address_city',
        'address_state', 'address_postcode', 'address_country',
    )

    def __init__(self, session, **kwargs):
        super(OrganizationAdminView, self).__init__(Organization, session, name='Organizations', **kwargs)

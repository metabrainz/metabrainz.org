from flask import Blueprint, render_template, flash
from metabrainz.decorators import requires_auth
from metabrainz.model.donation import Donation
from metabrainz.admin.forms import AddDonationForm
from metabrainz.donations.receipts import send_receipt

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/add-donation', methods=['GET', 'POST'])
@requires_auth
def add_donation():
    form = AddDonationForm()

    if form.validate_on_submit():
        new_donation = Donation.add_donation(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            editor=form.editor.data,
            amount=form.amount.data,
            fee=form.fee.data,
            address_street=form.address_street.data,
            address_city=form.address_city.data,
            address_state=form.address_state.data,
            address_postcode=form.address_postcode.data,
            address_country=form.address_country.data,
            payment_date=form.payment_date.data,
            can_contact=form.can_contact.data,
            anonymous=form.anonymous.data,
        )
        flash('Donation has been added. (ID: %s, Amount: %s, Fee: %s)'
              % (new_donation.id, new_donation.amount, new_donation.fee),
              'success')
        send_receipt(
            new_donation.email,
            new_donation.timestamp,
            new_donation.amount,
            '%s %s' % (new_donation.first_name, new_donation.last_name),
            new_donation.moderator,
        )

    return render_template('admin/add_donation.html', form=form)

from flask import Blueprint, request, render_template, url_for, redirect
from metabrainz.model.donation import Donation

finances_bp = Blueprint('finances', __name__)


@finances_bp.route('/')
def index():
    return render_template('finances/finances.html')


@finances_bp.route('/donations')
def donations():
    page = int(request.args.get('page', default=1))
    if page < 1:
        return redirect(url_for('.donations'))
    limit = 30
    offset = (page - 1) * limit
    count, donations = Donation.get_recent_donations(limit=limit, offset=offset)
    return render_template('finances/donations.html', donations=donations,
                           page=page, limit=limit, count=count)

@finances_bp.route('/highest-donors')
def highest_donors():
    page = int(request.args.get('page', default=1))
    if page < 1:
        return redirect(url_for('.donations'))
    limit = 30
    offset = (page - 1) * limit
    count, donations = Donation.get_biggest_donations(limit=limit, offset=offset)
    return render_template('finances/highest-donors.html', donations=donations,
                           page=page, limit=limit, count=count)

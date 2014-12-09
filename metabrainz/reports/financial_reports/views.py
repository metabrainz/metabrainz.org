from __future__ import division
from flask import Blueprint, request, render_template, url_for, redirect
from metabrainz.model.donation import Donation
from math import ceil

financial_reports_bp = Blueprint('financial_reports', __name__, static_folder='files')


@financial_reports_bp.route('/')
def index():
    return render_template('financial_reports/index.html')


@financial_reports_bp.route('/donations')
def donations():
    page = int(request.args.get('page', default=1))
    if page < 1:
        return redirect(url_for('.donations'))
    limit = 30
    offset = (page - 1) * limit
    count, donations = Donation.get_recent_donations(limit=limit, offset=offset)

    last_page = int(ceil(count / limit))
    if page > last_page:
        return redirect(url_for('.donations', page=last_page))

    return render_template('financial_reports/donations.html', donations=donations,
                           page=page, last_page=last_page)


@financial_reports_bp.route('/highest-donors')
def highest_donors():
    page = int(request.args.get('page', default=1))
    if page < 1:
        return redirect(url_for('.highest_donors'))
    limit = 30
    offset = (page - 1) * limit
    count, donations = Donation.get_biggest_donations(limit=limit, offset=offset)

    last_page = int(ceil(count / limit))
    if page > last_page:
        return redirect(url_for('.highest_donors', page=last_page))

    return render_template('financial_reports/highest-donors.html', donations=donations,
                           page=page, last_page=last_page)

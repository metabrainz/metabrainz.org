from decimal import Decimal
from flask import Response, request, redirect, url_for
from flask_admin import expose
from metabrainz.admin import AdminIndexView, AdminBaseView, forms
from metabrainz.model.supporter import Supporter, STATE_PENDING, STATE_ACTIVE, STATE_REJECTED, STATE_WAITING, STATE_LIMITED
from metabrainz.model.token import Token
from metabrainz.model.token_log import TokenLog
from metabrainz.model.access_log import AccessLog
from metabrainz.db import supporter as db_supporter
from metabrainz.db import payment as db_payment
from metabrainz import flash
from brainzutils import cache
from werkzeug.utils import secure_filename
import werkzeug.datastructures
import os.path
import logging
import time
import uuid
import json
import socket

from metabrainz.utils import get_int_query_param


class HomeView(AdminIndexView):

    @expose('/')
    def index(self):
        return self.render(
            'admin/home.html',
            pending_supporters=Supporter.get_all(state=STATE_PENDING),
            waiting_supporters=Supporter.get_all(state=STATE_WAITING),
        )


class SupportersView(AdminBaseView):

    @expose('/')
    def index(self):
        value = request.args.get('value')
        results = Supporter.search(value) if value else []
        return self.render('admin/users/index.html',
                           value=value, results=results)

    @expose('/<int:supporter_id>')
    def details(self, supporter_id):
        supporter = Supporter.get(id=supporter_id)
        active_tokens = Token.get_all(owner_id=supporter.id, is_active=True)
        return self.render(
            'admin/users/details.html',
            supporter=supporter,
            active_tokens=active_tokens,
        )

    @expose('/<int:supporter_id>/edit', methods=('GET', 'POST'))
    def edit(self, supporter_id):
        supporter = Supporter.get(id=supporter_id)

        form = forms.SupporterEditForm(defaults={
            'musicbrainz_id': supporter.musicbrainz_id,
            'contact_name': supporter.contact_name,
            'contact_email': supporter.contact_email,
            'state': supporter.state,
            'is_commercial': supporter.is_commercial,
            'org_name': supporter.org_name,
            'org_desc': supporter.org_desc,
            'api_url': supporter.api_url,
            'address_street': supporter.address_street,
            'address_city': supporter.address_city,
            'address_state': supporter.address_state,
            'address_postcode': supporter.address_postcode,
            'address_country': supporter.address_country,
            'tier': supporter.tier_id,
            'amount_pledged': supporter.amount_pledged or 0,
            'featured': supporter.featured,
            'website_url': supporter.website_url,
            'logo_url': supporter.org_logo_url,
            'usage_desc': supporter.data_usage_desc,
            'good_standing': supporter.good_standing,
            'in_deadbeat_club': supporter.in_deadbeat_club,
        })

        if form.validate_on_submit():
            update_data = {
                'musicbrainz_id': form.musicbrainz_id.data,
                'contact_name': form.contact_name.data,
                'contact_email': form.contact_email.data,
                'state': form.state.data,
                'is_commercial': form.is_commercial.data,
                'org_name': form.org_name.data,
                'org_desc': form.org_desc.data,
                'api_url': form.api_url.data,
                'address_street': form.address_street.data,
                'address_city': form.address_city.data,
                'address_state': form.address_state.data,
                'address_postcode': form.address_postcode.data,
                'address_country': form.address_country.data,
                'tier_id': int(form.tier.data) if form.tier.data != 'None' else None,
                'amount_pledged': form.amount_pledged.data,
                'featured': form.featured.data,
                'website_url': form.website_url.data,
                'org_logo_url': form.logo_url.data,
                'data_usage_desc': form.usage_desc.data,
                'good_standing': form.good_standing.data,
                'in_deadbeat_club': form.in_deadbeat_club.data,
            }
            if form.logo.data:
                extension = os.path.splitext(secure_filename(form.logo.data.filename))[1]
                # Using a random UUID instead of supporter ID here so that we don't unnecessarily expose them.
                logo_filename = '%s%s' % (uuid.uuid4(), extension)
                update_data['logo_filename'] = logo_filename
                image_storage = form.logo.data  # type: werkzeug.datastructures.FileStorage
                if supporter.logo_filename:
                    # Deleting old logo
                    try:
                        os.remove(os.path.join(forms.LOGO_STORAGE_DIR, supporter.logo_filename))
                    except OSError as e:
                        logging.warning(e)
                # Saving new one
                image_storage.save(os.path.join(forms.LOGO_STORAGE_DIR, logo_filename))
            db_supporter.update(supporter_id=supporter.id, **update_data)
            return redirect(url_for('.details', supporter_id=supporter.id))

        return self.render(
            'admin/users/edit.html',
            supporter=supporter,
            form=form,
        )

    @expose('/<int:supporter_id>/stats')
    def details_stats(self, supporter_id):
        stats = AccessLog.get_hourly_usage(supporter_id=supporter_id)
        return Response(json.dumps([{'data': [[
                time.mktime(i[0].utctimetuple()) * 1000,
                i[1]
            ] for i in stats]}]),
            content_type='application/json; charset=utf-8')

    @expose('/approve')
    def approve(self):
        supporter_id = request.args.get('supporter_id')
        if request.args.get('limited'):
            Supporter.get(id=supporter_id).set_state(STATE_LIMITED)
        else:
            Supporter.get(id=supporter_id).set_state(STATE_ACTIVE)
        flash.info('Supporter #%s has been approved.' % supporter_id)

        # Redirecting to the next pending supporter
        next_supporter = Supporter.get(state=STATE_PENDING)
        if next_supporter:
            return redirect(url_for('.details', supporter_id=next_supporter.id))
        else:
            flash.info('No more pending supporters.')
            return redirect(url_for('.index'))

    @expose('/reject')
    def reject(self):
        supporter_id = request.args.get('supporter_id')
        Supporter.get(id=supporter_id).set_state(STATE_REJECTED)
        flash.warning('Supporter #%s has been rejected.' % supporter_id)

        # Redirecting to the next pending supporter
        next_supporter = Supporter.get(state=STATE_PENDING)
        if next_supporter:
            return redirect(url_for('.details', supporter_id=next_supporter.id))
        else:
            flash.info('No more pending supporters.')
            return redirect(url_for('.index'))

    @expose('/wait')
    def wait(self):
        supporter_id = request.args.get('supporter_id')
        Supporter.get(id=supporter_id).set_state(STATE_WAITING)
        flash.info('Supporter #%s has been put into the waiting list.' % supporter_id)

        # Redirecting to the next pending supporter
        next_supporter = Supporter.get(state=STATE_PENDING)
        if next_supporter:
            return redirect(url_for('.details', supporter_id=next_supporter.id))
        else:
            flash.info('No more pending supporters.')
            return redirect(url_for('.index'))

    @expose('/revoke-token')
    def revoke_token(self):
        token_value = request.args.get('token_value')
        token = Token.get(value=token_value)
        token.revoke()
        flash.info('Token %s has been revoked.' % token_value)
        return redirect(url_for('.details', supporter_id=token.owner_id))


class CommercialSupportersView(AdminBaseView):

    @expose('/')
    def index(self):
        page = get_int_query_param('page', default=1)
        if page < 1:
            return redirect(url_for('.index'))
        limit = 20
        offset = (page - 1) * limit
        supporters, count = Supporter.get_all_commercial(limit=limit, offset=offset)
        return self.render('admin/commercial-users/index.html', supporters=supporters,
                           page=page, limit=limit, count=count)


class PaymentsView(AdminBaseView):

    @expose('/')
    def list(self):
        page = get_int_query_param('page', default=1)
        is_donation_arg = request.args.get('is_donation')
        if is_donation_arg == "True":
            is_donation = True
        elif is_donation_arg == "False":
            is_donation = False
        else:
            is_donation = None
        if page < 1:
            return redirect(url_for('.list'))
        limit = 40
        offset = (page - 1) * limit
        payments, count = db_payment.list_payments(is_donation=is_donation, limit=limit, offset=offset)
        return self.render('admin/payments/list.html', payments=payments, is_donation=is_donation,
                           page=page, limit=limit, count=count)


class TokensView(AdminBaseView):

    @expose('/')
    def index(self):
        value = request.args.get('value')
        results = Token.search_by_value(value) if value else []
        return self.render('admin/tokens/search.html',
                           value=value, results=results)


class StatsView(AdminBaseView):

    IP_ADDR_TIMEOUT = 10

    @expose('/')
    def overview(self):
        return self.render(
            'admin/stats/overview.html',
            active_supporter_count=AccessLog.active_supporter_count(),
            top_downloaders=AccessLog.top_downloaders(10),
            token_actions=TokenLog.list(10)[0],
        )

    @staticmethod
    def dns_lookup(ip):
        try:
            data = socket.gethostbyaddr(ip)
            return data[0]
        except Exception as err:
            return None


    @staticmethod
    def lookup_ips(supporters):
        """ Try to lookup and cache as many reverse DNS as possible in a window of time """

        data = []
        timeout = time.monotonic() + StatsView.IP_ADDR_TIMEOUT
        for supporter in supporters:
            row = list(supporter)

            reverse = cache.get(supporter[0])
            if not reverse: 
                if time.monotonic() < timeout:
                    reverse = StatsView.dns_lookup(supporter[0])
                else:
                    reverse = None

            if reverse:
                cache.set(supporter[0], reverse, 3600)
                row[0] = reverse

            data.append(row)

        return data


    @expose('/top-ips/')
    def top_ips(self):
        days = get_int_query_param('days', default=7)

        non_commercial, commercial = AccessLog.top_ips(limit=100, days=days)

        non_commercial = StatsView.lookup_ips(non_commercial)
        commercial = StatsView.lookup_ips(commercial)
            
        return self.render(
            'admin/stats/top-ips.html',
            non_commercial=non_commercial,
            commercial=commercial,
            days=days
        )

    @expose('/top-tokens/')
    def top_tokens(self):
        days = get_int_query_param('days', default=7)

        non_commercial, commercial = AccessLog.top_tokens(limit=100, days=days)
        return self.render(
            'admin/stats/top-tokens.html',
            non_commercial=non_commercial,
            commercial=commercial,
            days=days
        )


    @expose('/token-log')
    def token_log(self):
        page = get_int_query_param('page', default=1)
        if page < 1:
            return redirect(url_for('.token_log'))
        limit = 20
        offset = (page - 1) * limit
        token_actions, count = TokenLog.list(limit=limit, offset=offset)
        return self.render(
            'admin/stats/token-log.html',
            token_actions=token_actions,
            page=page,
            limit=limit,
            count=count,
        )

    @expose('/usage')
    def hourly_usage_data(self):
        stats = AccessLog.get_hourly_usage()
        return Response(json.dumps([{'data': [[
                time.mktime(i[0].utctimetuple()) * 1000,
                i[1]
            ] for i in stats]}]),
            content_type='application/json; charset=utf-8')


    @expose('/supporters/')
    def supporters(self):

        total = Decimal()
        supporters = Supporter.get_active_supporters()
        for supporter in supporters:
            total += supporter.amount_pledged
            
        return self.render(
            'admin/stats/users.html',
            supporters=supporters,
            total=total
        )

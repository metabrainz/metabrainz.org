from flask import Response, request, redirect, url_for
from flask_admin import expose
from metabrainz.admin import AdminIndexView, AdminBaseView, forms
from metabrainz.model.user import User, STATE_PENDING, STATE_ACTIVE, STATE_REJECTED, STATE_WAITING, STATE_LIMITED
from metabrainz.model.token import Token
from metabrainz.model.token_log import TokenLog
from metabrainz.model.access_log import AccessLog
from metabrainz.db import user as db_user
from metabrainz import flash
from werkzeug.utils import secure_filename
import werkzeug.datastructures
import os.path
import logging
import time
import uuid
import json


class HomeView(AdminIndexView):

    @expose('/')
    def index(self):
        return self.render(
            'admin/home.html',
            pending_users=User.get_all(state=STATE_PENDING),
            waiting_users=User.get_all(state=STATE_WAITING),
        )


class UsersView(AdminBaseView):

    @expose('/')
    def index(self):
        value = request.args.get('value')
        results = User.search(value) if value else []
        return self.render('admin/users/index.html',
                           value=value, results=results)

    @expose('/<int:user_id>')
    def details(self, user_id):
        user = User.get(id=user_id)
        active_tokens = Token.get_all(owner_id=user.id, is_active=True)
        return self.render(
            'admin/users/details.html',
            user=user,
            active_tokens=active_tokens,
        )

    @expose('/<int:user_id>/edit', methods=('GET', 'POST'))
    def edit(self, user_id):
        user = User.get(id=user_id)

        form = forms.UserEditForm(defaults={
            'musicbrainz_id': user.musicbrainz_id,
            'contact_name': user.contact_name,
            'contact_email': user.contact_email,
            'state': user.state,
            'is_commercial': user.is_commercial,
            'org_name': user.org_name,
            'org_desc': user.org_desc,
            'api_url': user.api_url,
            'address_street': user.address_street,
            'address_city': user.address_city,
            'address_state': user.address_state,
            'address_postcode': user.address_postcode,
            'address_country': user.address_country,
            'tier': user.tier_id,
            'amount_pledged': user.amount_pledged or 0,
            'featured': user.featured,
            'website_url': user.website_url,
            'logo_url': user.org_logo_url,
            'usage_desc': user.data_usage_desc,
            'good_standing': user.good_standing,
            'in_deadbeat_club': user.in_deadbeat_club,
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
                # Using a random UUID instead of user ID here so that we don't unnecessarily expose them.
                logo_filename = '%s%s' % (uuid.uuid4(), extension)
                update_data['logo_filename'] = logo_filename
                image_storage = form.logo.data  # type: werkzeug.datastructures.FileStorage
                if user.logo_filename:
                    # Deleting old logo
                    try:
                        os.remove(os.path.join(forms.LOGO_STORAGE_DIR, user.logo_filename))
                    except OSError as e:
                        logging.warning(e)
                # Saving new one
                image_storage.save(os.path.join(forms.LOGO_STORAGE_DIR, logo_filename))
            db_user.update(user_id=user.id, **update_data)
            return redirect(url_for('.details', user_id=user.id))

        return self.render(
            'admin/users/edit.html',
            user=user,
            form=form,
        )

    @expose('/<int:user_id>/stats')
    def details_stats(self, user_id):
        stats = AccessLog.get_hourly_usage(user_id=user_id)
        return Response(json.dumps([{'data': [[
                time.mktime(i[0].utctimetuple()) * 1000,
                i[1]
            ] for i in stats]}]),
            content_type='application/json; charset=utf-8')

    @expose('/approve')
    def approve(self):
        user_id = request.args.get('user_id')
        if request.args.get('limited'):
            User.get(id=user_id).set_state(STATE_LIMITED)
        else:
            User.get(id=user_id).set_state(STATE_ACTIVE)
        flash.info('User #%s has been approved.' % user_id)

        # Redirecting to the next pending user
        next_user = User.get(state=STATE_PENDING)
        if next_user:
            return redirect(url_for('.details', user_id=next_user.id))
        else:
            flash.info('No more pending users.')
            return redirect(url_for('.index'))

    @expose('/reject')
    def reject(self):
        user_id = request.args.get('user_id')
        User.get(id=user_id).set_state(STATE_REJECTED)
        flash.warn('User #%s has been rejected.' % user_id)

        # Redirecting to the next pending user
        next_user = User.get(state=STATE_PENDING)
        if next_user:
            return redirect(url_for('.details', user_id=next_user.id))
        else:
            flash.info('No more pending users.')
            return redirect(url_for('.index'))

    @expose('/wait')
    def wait(self):
        user_id = request.args.get('user_id')
        User.get(id=user_id).set_state(STATE_WAITING)
        flash.info('User #%s has been put into the waiting list.' % user_id)

        # Redirecting to the next pending user
        next_user = User.get(state=STATE_PENDING)
        if next_user:
            return redirect(url_for('.details', user_id=next_user.id))
        else:
            flash.info('No more pending users.')
            return redirect(url_for('.index'))

    @expose('/revoke-token')
    def revoke_token(self):
        token_value = request.args.get('token_value')
        token = Token.get(value=token_value)
        token.revoke()
        flash.info('Token %s has been revoked.' % token_value)
        return redirect(url_for('.details', user_id=token.owner_id))


class CommercialUsersView(AdminBaseView):

    @expose('/')
    def index(self):
        page = int(request.args.get('page', default=1))
        if page < 1:
            return redirect(url_for('.index'))
        limit = 20
        offset = (page - 1) * limit
        users, count = User.get_all_commercial(limit=limit, offset=offset)
        return self.render('admin/commercial-users/index.html', users=users,
                           page=page, limit=limit, count=count)


class TokensView(AdminBaseView):

    @expose('/')
    def index(self):
        value = request.args.get('value')
        results = Token.search_by_value(value) if value else []
        return self.render('admin/tokens/search.html',
                           value=value, results=results)


class StatsView(AdminBaseView):

    @expose('/')
    def overview(self):
        return self.render(
            'admin/stats/overview.html',
            active_user_count=AccessLog.active_user_count(),
            top_downloaders=AccessLog.top_downloaders(10),
            token_actions=TokenLog.list(10)[0],
        )

    @expose('/token-log')
    def token_log(self):
        page = int(request.args.get('page', default=1))
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

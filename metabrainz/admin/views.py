from flask_admin import BaseView, expose
from metabrainz.model.user import User, STATE_PENDING, STATE_ACTIVE, STATE_REJECTED
from metabrainz.model.token import Token
from metabrainz import flash
from flask import request, redirect, url_for


class UsersView(BaseView):

    @expose('/')
    def index(self):
        users = User.get_all(state=STATE_PENDING)
        return self.render('admin/users/index.html', users=users)

    @expose('/<int:user_id>')
    def details(self, user_id):
        user = User.get(id=user_id)
        active_tokens = Token.get_all(owner_id=user.id, is_active=True)
        return self.render('admin/users/details.html', user=user,
                           active_tokens=active_tokens)

    @expose('/approve')
    def approve(self):
        user_id = request.args.get('user_id')
        User.get(id=user_id).set_state(STATE_ACTIVE)
        flash.info("User #%s has been approved." % user_id)

        # Redirecting to the next pending user
        next_user = User.get(state=STATE_PENDING)
        if next_user:
            return redirect(url_for('.details', user_id=next_user.id))
        else:
            return redirect(url_for('.index'))

    @expose('/reject')
    def reject(self):
        user_id = request.args.get('user_id')
        User.get(id=user_id).set_state(STATE_REJECTED)
        flash.warn("User #%s has been rejected." % user_id)

        # Redirecting to the next pending user
        next_user = User.get(state=STATE_PENDING)
        if next_user:
            return redirect(url_for('.details', user_id=next_user.id))
        else:
            return redirect(url_for('.index'))

    @expose('/revoke-token')
    def revoke_token(self):
        token_value = request.args.get('token_value')
        token = Token.get(value=token_value)
        token.revoke()
        flash.info("Token %s has been revoked." % token_value)
        return redirect(url_for('.details', user_id=token.owner_id))


class TokensView(BaseView):

    @expose('/')
    def index(self):
        value = request.args.get('value')
        results = Token.search_by_value(value) if value else []
        return self.render('admin/tokens/search.html',
                           value=value, results=results)

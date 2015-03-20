from flask_admin import Admin, BaseView, expose
from metabrainz.model.user import User, STATE_PENDING


class UsersView(BaseView):

    @expose('/')
    def index(self):
        users = User.get_all(state=STATE_PENDING)
        return self.render('admin/users/index.html', users=users)

    @expose('/<int:user_id>')
    def details(self, user_id):
        return self.render('admin/users/details.html',
                           user=User.get(id=user_id))


class TokensView(BaseView):

    @expose('/')
    def index(self):
        # TODO: Implement token search (search results should have
        # "revoke" button and a lit to user if token is associated
        # with one.
        return self.render('admin/tokens/index.html')

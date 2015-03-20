from flask_admin import Admin, BaseView, expose


class UsersView(BaseView):

    @expose('/')
    def index(self):
        # TODO: Show list of users that are pending approval
        # (with links to user details page).
        return self.render('admin/users/index.html')

    @expose('/<int:user_id>')
    def details(self, user_id):
        # TODO: Show info about user and status update buttons.
        return self.render('admin/users/details.html')


class TokensView(BaseView):

    @expose('/')
    def index(self):
        # TODO: Implement token search (search results should have
        # "revoke" button and a lit to user if token is associated
        # with one.
        return self.render('admin/tokens/index.html')

from flask_admin import BaseView, AdminIndexView as IndexView
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import SecureForm
from flask_login import current_user
from flask import request, redirect, url_for, current_app


class AuthMixin(object):
    """All admin views that shouldn't be available to public, must subclass this."""

    def is_accessible(self):
        return current_user.is_authenticated and current_user.name in current_app.config['ADMINS']

    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            return redirect(url_for('users.login', next=request.url))


class AdminBaseView(AuthMixin, BaseView): pass
class AdminModelView(AuthMixin, ModelView):
    """Admin model view with CSRF protection enabled."""
    form_base_class = SecureForm

class AdminIndexView(AuthMixin, IndexView): pass

from flask_babel import gettext
from flask_wtf import FlaskForm
from wtforms import StringField, validators, FieldList
from wtforms.utils import unset_value


class FormikFieldList(FieldList):

    def _extract_indices(self, prefix, formdata):
        """
        Yield indices of any keys with given prefix.

        formdata must be an object which will produce keys when iterated.  For
        example, if field 'foo' contains keys 'foo-0-bar', 'foo-1-baz', then
        the numbers 0 and 1 will be yielded, but not neccesarily in order.
        """
        offset = len(prefix) + 1
        for k in formdata:
            if k.startswith(prefix):
                k = k[offset:].split('.', 1)[0]
                if k.isdigit():
                    yield int(k)

    def _add_entry(self, formdata=None, data=unset_value, index=None):
        assert not self.max_entries or len(self.entries) < self.max_entries, \
            'You cannot have more than max_entries entries in this FieldList'
        if index is None:
            index = self.last_index + 1
        self.last_index = index
        name = '%s.%d' % (self.short_name, index)
        id = '%s.%d' % (self.id, index)
        field = self.unbound_field.bind(form=None, name=name, prefix=self._prefix, id=id, _meta=self.meta,
                                        translations=self._translations)
        field.process(formdata, data)
        self.entries.append(field)
        return field


class CustomURLValidator(object):
    """
    Use in conjunction with validators.URL(require_tld=False) to allow localhost urls but ban javascript URIs.
    """
    field_flags = ('required', )

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        if not field.data.startswith(("http://", "https://")):
            if self.message:
                error = self.message
            else:
                error = f"{field.name} must use http or https."
            raise validators.ValidationError(error)


class ApplicationForm(FlaskForm):
    client_name = StringField(gettext('Application Name'), [
        validators.InputRequired(message=gettext("Application name field is empty.")),
        validators.Length(min=3, message=gettext("Application name needs to be at least 3 characters long.")),
        validators.Length(max=64, message=gettext("Application name needs to be at most 64 characters long."))
    ])
    description = StringField(gettext('Description'), [
        validators.InputRequired(message=gettext("Client description field is empty.")),
        validators.Length(min=3, message=gettext("Client description needs to be at least 3 characters long.")),
        validators.Length(max=512, message=gettext("Client description needs to be at most 512 characters long."))
    ])
    website = StringField(gettext('Homepage'), [
        validators.InputRequired(message=gettext("Homepage field is empty.")),
        validators.URL(require_tld=False, message=gettext("Homepage is not a valid URI.")),
        CustomURLValidator(message=gettext("Homepage URL must use http or https"))
    ])
    redirect_uris = FormikFieldList(StringField(gettext('Authorization callback URL'), [
        validators.InputRequired(message=gettext("Authorization callback URL field is empty.")),
        validators.URL(require_tld=False, message=gettext("Authorization callback URL is invalid.")),
        CustomURLValidator(message=gettext("Authorization callback URL must use http or https."))
    ]), min_entries=1)


class AuthorizationForm(FlaskForm):
    confirm = StringField(gettext('Confirm'), [validators.DataRequired()])

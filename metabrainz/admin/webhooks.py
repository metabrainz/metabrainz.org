import secrets
from urllib.parse import urlparse

from flask import redirect, url_for, flash, request, current_app
from flask_admin import expose
from flask_admin.actions import action
from markupsafe import Markup
from wtforms import StringField, BooleanField, SelectMultipleField, ValidationError
from wtforms.validators import DataRequired
from wtforms.widgets import ListWidget, CheckboxInput

from metabrainz.admin import AdminModelView
from metabrainz.model import db
from metabrainz.model.webhook import Webhook, WebhookDelivery, EVENT_USER_CREATED, EVENT_USER_DELETED, \
    EVENT_USER_VERIFIED, EVENT_USER_UPDATED


def validate_webhook_url(form, field):
    """Custom validator for webhook URLs.
    
    - Allow localhost URLs with http or https
    - Require https for all other URLs
    - Disallow javascript: and other dangerous protocols
    """
    url = field.data
    if not url:
        return
    
    try:
        parsed = urlparse(url)

        if not parsed.scheme:
            raise ValidationError("URL must include a protocol (http:// or https://).")

        scheme = parsed.scheme.lower().lower()
        if scheme not in ("http", "https"):
            raise ValidationError("Invalid URL protocol. Only HTTP and HTTPS are allowed.")

        if not parsed.hostname:
            raise ValidationError("URL must include a valid hostname.")

        is_localhost = parsed.hostname in ("localhost", "127.0.0.1", "::1") or \
                      (parsed.hostname and parsed.hostname.startswith("192.168.")) or \
                      (parsed.hostname and parsed.hostname.startswith("10.")) or \
                      (parsed.hostname and parsed.hostname.startswith("172."))

        if not is_localhost and scheme == "http":
            raise ValidationError("Non-localhost URLs must use https://.")

    except ValueError as e:
        raise ValidationError(f"Invalid URL: {str(e)}")


class EventsMultiSelectField(SelectMultipleField):
    """Custom multi-select field for webhook events with checkboxes."""
    widget = ListWidget(prefix_label=True)
    option_widget = CheckboxInput()
    
    def pre_validate(self, form):
        """Validate that selected values are in the choices."""
        if self.data:
            values = [choice[0] for choice in self.choices]
            for value in self.data:
                if value not in values:
                    raise ValueError(f"'{value}' is not a valid choice for this field")


class WebhookModelView(AdminModelView):
    """Flask-Admin view for managing webhooks."""
    
    column_list = ("name", "url", "events", "is_active", "created_at")
    column_searchable_list = ("name", "url")
    column_filters = ("is_active", "created_at")
    column_default_sort = ("created_at", True)

    create_template = "admin/webhook/create.html"
    edit_template = "admin/webhook/edit.html"

    # Form configuration - exclude secret from form (auto-generated)
    form_columns = ("name", "url", "events", "is_active")
    form_extra_fields = {
        "name": StringField(
            "Name",
            validators=[DataRequired()],
            description="A descriptive name for this webhook."
        ),
        "url": StringField(
            "URL",
            validators=[DataRequired(), validate_webhook_url],
            description="The URL that will receive the webhook events. Use https:// for production URLs (http:// allowed for localhost)."
        ),
        "events": EventsMultiSelectField(
            "Events",
            choices=[
                (EVENT_USER_CREATED, "User Created"),
                (EVENT_USER_DELETED, "User Deleted"),
                (EVENT_USER_VERIFIED, "User Verified"),
                (EVENT_USER_UPDATED, "User Updated"),
            ],
            validators=[DataRequired()],
            description="Select which events this webhook should receive."
        ),
        "is_active": BooleanField(
            "Active",
            default=True,
            description="Inactive webhooks will not send any events."
        ),
    }

    can_create = True
    can_edit = True

    def __init__(self, session, **kwargs):
        super().__init__(Webhook, session, **kwargs)
    
    def on_model_change(self, form, model, is_created):
        """Auto-generate secret key on creation and show it to the user."""
        if is_created:
            model.secret = "mebw_" + secrets.token_hex(32)
            flash(Markup(
                f"<strong>Webhook created successfully!</strong> "
                f"Please copy and save the secret key: <code>{model.secret}</code>. "
                "You will not be able to see it again."
            ), "success")


class WebhookDeliveryModelView(AdminModelView):
    """Flask-Admin view for managing webhook deliveries."""
    
    column_list = ("event_type", "webhook", "status", "response_status", "retry_count", "created_at")
    column_searchable_list = ("event_type",)
    column_filters = ("webhook", "event_type", "status", "response_status", "created_at")
    column_default_sort = ("created_at", True)
    
    column_formatters = {
        "status": lambda v, c, m, p: _format_status_badge(m.status, m.retry_count),
        "response_status": lambda v, c, m, p: _format_response_status(m.response_status),
        "webhook": lambda v, c, m, p: _format_webhook_link(m.webhook),
    }
    
    column_labels = {
        "event_type": "Event Type",
        "webhook": "Webhook",
        "status": "Status",
        "response_status": "HTTP Status",
        "retry_count": "Retries",
        "created_at": "Created At",
    }
    
    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True

    def __init__(self, session, **kwargs):
        super().__init__(WebhookDelivery, session, **kwargs)

    @expose("/details/")
    def details_view(self):
        """Custom details view."""
        return_url = self.get_url(".index_view")
        
        # Get the ID from the query string
        deliver_id = request.args.get("id")
        if not deliver_id:
            flash("No delivery ID provided.", "error")
            return redirect(return_url)
        
        model = self.get_one(deliver_id)
        if model is None:
            flash("Delivery not found.", "error")
            return redirect(return_url)
        
        return self.render(
            "admin/webhook_deliveries/details.html",
            model=model,
            return_url=return_url
        )

    @action("retry_failed", "Retry Failed Deliveries", "Are you sure you want to retry the selected failed deliveries?")
    def action_retry_failed(self, ids):
        """Retry selected failed deliveries."""
        try:
            query = WebhookDelivery.query.filter(
                WebhookDelivery.id.in_(ids)
            )
            
            count = 0
            skipped = 0
            for delivery in query.all():
                if delivery.status in ["failed", "pending"]:
                    delivery.status = "pending"
                    delivery.error_message = None
                    count += 1
                else:
                    skipped += 1
            
            db.session.commit()
            
            if count > 0:
                flash(f"Queued {count} delivery(ies) for retry.", "success")
            if skipped > 0:
                flash(f"Skipped {skipped} delivery(ies) (only failed/pending can be retried).", "info")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error retrying deliveries: {str(e)}", exc_info=True)
            flash("Failed to retry deliveries. Please try again.", "error")
    
    @expose("/retry/<delivery_id>", methods=["POST"])
    def retry_delivery(self, delivery_id):
        """Retry a single delivery from the detail page."""
        try:
            delivery = WebhookDelivery.query.get_or_404(delivery_id)
            
            if delivery.status not in ["failed", "pending"]:
                flash(
                    f"Cannot retry delivery with status: {delivery.status}. "
                    f"Only failed or pending deliveries can be retried.",
                    "warning"
                )
                return redirect(url_for(".details_view", id=delivery_id))
            
            delivery.status = "pending"
            delivery.error_message = None
            db.session.commit()
            
            flash("Delivery has been queued for retry.", "success")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error retrying delivery {delivery_id}: {str(e)}", exc_info=True)
            flash(f"Error retrying delivery: {str(e)}", "error")
        
        return redirect(url_for(".details_view", id=delivery_id))


def _format_status_badge(status, retry_count):
    """Format status as a colored badge."""    
    badge_class = {
        "delivered": "success",
        "failed": "danger",
        "processing": "info",
        "pending": "warning",
    }.get(status, "default")
    
    icon = {
        "delivered": "check-circle",
        "failed": "times-circle",
        "processing": "spinner fa-spin",
        "pending": "clock",
    }.get(status, "question-circle")
    
    retry_text = f" ({retry_count} retries)" if retry_count > 0 else ""
    
    return Markup(
        f'<span class="label label-{badge_class}">'
        f'<i class="fa fa-{icon}"></i> {status.title()}{retry_text}'
        f'</span>'
    )


def _format_response_status(response_status):
    """Format HTTP response status as a colored badge."""    
    if not response_status:
        return ""
    
    if response_status >= 500:
        badge_class = "danger"
    elif response_status >= 400:
        badge_class = "warning"
    elif response_status >= 300:
        badge_class = "info"
    else:
        badge_class = "success"
    
    return Markup(f'<span class="label label-{badge_class}">{response_status}</span>')


def _format_webhook_link(webhook):
    """Format webhook as a link with name."""    
    if not webhook:
        return ""
    
    name = webhook.name if webhook.name else webhook.url[:40] + ("..." if len(webhook.url) > 40 else "")
    
    return Markup(
        f'<a href="{url_for("webhooks-admin.edit_view", id=webhook.id)}" class="btn btn-xs btn-info">'
        f'<i class="fa fa-link"></i> {name}'
        f"</a>"
    )

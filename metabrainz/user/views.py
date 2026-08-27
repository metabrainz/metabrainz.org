import hmac
import json
import re
from datetime import datetime, timezone

from flask import Blueprint, current_app, redirect, render_template, request, url_for, jsonify
from flask_login import confirm_login, logout_user, login_required, login_user, current_user
from flask_wtf.csrf import generate_csrf
from sqlalchemy.exc import IntegrityError

from metabrainz import bcrypt, flash
from metabrainz.index.forms import MeBFlaskForm
from metabrainz.model import db
from metabrainz.model.user import User, UsernameNotAllowedException
from metabrainz.model.webhook import EVENT_USER_CREATED, EVENT_USER_UPDATED
from metabrainz.oauth.registration_request import get_registration_request
from metabrainz.user import login_forbidden
from metabrainz.user.email import send_forgot_password_email, send_forgot_username_email, create_email_link_checksum, \
    create_reset_password_checksum, VERIFY_EMAIL, send_verification_email
from metabrainz.user.forms import UserLoginForm, UserReauthenticationForm, UserSignupForm, ForgotPasswordForm, \
    ForgotUsernameForm, ResetPasswordForm
from metabrainz.user.rate_limit import check_signup_rate_limit, increment_signup_count
from metabrainz.user.registration import validate_registration_email

users_bp = Blueprint("users", __name__)


# Mail clients that decode "&times" hand us "user_id=123×tamp=1699999999" and no timestamp,
# so pull both back out. Only links predating the "ts" rename can arrive this way.
_MANGLED_USER_ID_RE = re.compile(r"\A(?P<user_id>\d+)\u00d7tamp=(?P<timestamp>\d+)\Z")


def _parse_email_link_args():
    """Read the user id and timestamp out of an email link.

    Returns ``(user_id, timestamp, created_at)``, or None if the link is unusable. Keeps
    junk out of the database query, which raises rather than returning no user.
    """
    raw_user_id = request.args.get("user_id") or ""
    raw_timestamp = request.args.get("ts") or request.args.get("timestamp")

    mangled = _MANGLED_USER_ID_RE.match(raw_user_id)
    if mangled is not None:
        raw_user_id = mangled.group("user_id")
        if raw_timestamp is None:
            raw_timestamp = mangled.group("timestamp")

    try:
        user_id = int(raw_user_id)
        timestamp = int(raw_timestamp)
        created_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (OSError, OverflowError, TypeError, ValueError):
        return None
    return user_id, timestamp, created_at


def _checksum_matches(expected: str, received) -> bool:
    """Compare an email link checksum against the one we expect, in constant time."""
    if not received:
        return False
    return hmac.compare_digest(expected, received)


@users_bp.route("/privacy-summary")
def privacy_summary():
    return render_template("users/privacy-summary.html", props=json.dumps({}))


@users_bp.route("/signup", methods=["GET", "POST"])
@login_forbidden
def signup():
    """ User signup endpoint. """
    registration_request = get_registration_request(request.args.get("registration_request"))
    form = UserSignupForm()
    if request.method == "POST" and registration_request is not None:
        form.username.data = registration_request["username"]
        form.email.data = registration_request["email"]

    if form.validate_on_submit() and not check_signup_rate_limit(form):
        user = User.get(name=form.username.data)
        if user is not None:
            form.username.errors.append(f"Another user with username '{form.username.data}' exists.")
        else:
            # TODO: Handle the case where multiple users sign up with same email but haven"t verified it yet
            user = User.get(email=form.email.data)
            if user is not None:
                form.email.errors.append(f"Another user with email '{form.email.data}' exists.")
            else:
                try:
                    user = User.add(
                        name=form.username.data,
                        unconfirmed_email=form.email.data,
                        password=form.password.data
                    )
                    db.session.commit()
                    increment_signup_count()
                    user.emit_event(EVENT_USER_CREATED)

                    try:
                        send_verification_email(
                            user,
                            "Please verify your email address",
                            "email/user-email-address-verification.txt"
                        )
                    except Exception:
                        current_app.logger.exception(
                            "Error sending verification email for new user %s", user.id
                        )
                        flash.success("Account created.")
                        flash.error(
                            "The verification email could not be sent. "
                            "Please request a new one from your profile."
                        )
                    else:
                        flash.success("Account created. Please check your inbox to complete verification.")
                    login_user(user)
                    redirect_to = request.args.get("next") or url_for("index.home")
                    return redirect(redirect_to)
                except UsernameNotAllowedException:
                    form.username.errors.append("Username is not allowed.")
                    db.session.rollback()
                except IntegrityError:
                    # Two signups for the same username can race past the check above.
                    db.session.rollback()
                    form.username.errors.append(
                        f"Another user with username '{form.username.data}' exists."
                    )
                except Exception:
                    db.session.rollback()
                    flash.error("An unexpected error occurred. Please try again later.")
                    current_app.logger.exception("Error creating user")

    form_data = dict(**form.data)
    form_data.pop("csrf_token", None)
    if request.method == "GET" and registration_request is not None:
        form_data["username"] = registration_request["username"]
        form_data["email"] = registration_request["email"]

    return render_template("users/signup.html", props=json.dumps({
        "mtcaptcha_site_key": current_app.config.get("MTCAPTCHA_PUBLIC_KEY"),
        "csrf_token": generate_csrf(),
        "initial_form_data": form_data,
        "initial_errors": form.props_errors,
        "is_registration_request_signup": registration_request is not None,
        "registration_request_client_name": registration_request["client_name"]
        if registration_request is not None else None,
    }))


@users_bp.route("/login", methods=["GET", "POST"])
@login_forbidden
def login():
    """ User login endpoint. """
    form = UserLoginForm()
    if form.validate_on_submit():
        user = User.get(name=form.username.data)
        if user is None:
            form.username.errors.append(f"Username {form.username.data} not found.")
        else:
            if not bcrypt.check_password_hash(user.password, form.password.data):
                form.password.errors.append("Invalid username or password.")
            else:
                if user.is_blocked:
                    form.username.errors.append(
                        "Your account has been blocked. Please contact support if"
                        " you believe this is an error."
                    )
                else:
                    login_user(user, remember=form.remember_me.data)
                    user.last_login_at = datetime.now(timezone.utc)
                    user.update_remember_me(form.remember_me.data)
                    db.session.commit()

                    flash.success("Logged in successfully.")
                    redirect_to = request.args.get("next")
                    if not redirect_to:
                        redirect_to = url_for("index.home")
                    return redirect(redirect_to)

    form_errors = {k: ". ".join(v) for k, v in form.errors.items()}
    form_data = dict(**form.data)
    form_data.pop("csrf_token", None)
    registration_request = get_registration_request(request.args.get("registration_request"))
    if request.method == "GET" and registration_request is not None:
        form_data["username"] = registration_request["username"]

    return render_template("users/login.html", props=json.dumps({
        "mtcaptcha_site_key": current_app.config.get("MTCAPTCHA_PUBLIC_KEY"),
        "csrf_token": generate_csrf(),
        "initial_form_data": form_data,
        "initial_errors": form_errors
    }))


@users_bp.route("/reauthenticate", methods=["GET", "POST"])
@login_required
def reauthenticate():
    """Refresh the current login session before sensitive account actions."""
    form = UserReauthenticationForm()
    redirect_to = request.args.get("next") or url_for("index.profile")

    if form.validate_on_submit():
        if not bcrypt.check_password_hash(current_user.password, form.password.data):
            form.password.errors.append("Invalid password.")
        else:
            confirm_login()
            return redirect(redirect_to)

    return render_template(
        "users/reauthenticate.html",
        form=form,
    )


@users_bp.route("/verify-email")
def verify_email():
    """ User"s email verification endpoint. """
    parsed_link = _parse_email_link_args()
    if parsed_link is None:
        flash.error("Unable to verify email.")
        return redirect(url_for("index.home"))

    user_id, timestamp, created_at = parsed_link
    if created_at + current_app.config["EMAIL_VERIFICATION_EXPIRY"] <= datetime.now(timezone.utc):
        flash.error("Email verification link expired.")
        return redirect(url_for("index.home"))

    received_checksum = request.args.get("checksum")

    user = User.get(id=user_id)
    if user is None:
        flash.error("User not found.")
        return redirect(url_for("index.home"))

    checksum = create_email_link_checksum(VERIFY_EMAIL, user.id, user.unconfirmed_email, timestamp)
    if not _checksum_matches(checksum, received_checksum):
        flash.error("Unable to verify email.")
        return redirect(url_for("index.home"))

    if User.confirmed_email_exists(user.unconfirmed_email, exclude_user_id=user.id):
        flash.error(f"The email is already associated with an another account.")
        return redirect(url_for("index.home"))

    old_email = user.email
    user.email = user.unconfirmed_email
    user.unconfirmed_email = None
    user.email_confirmed_at = datetime.now(tz=timezone.utc)
    user.last_updated = user.email_confirmed_at
    db.session.commit()

    user.emit_event(
        EVENT_USER_UPDATED,
        old={"email": old_email},
        new={"email": user.email},
        updated_at=user.email_confirmed_at.isoformat(),
    )

    flash.success("Email verified!")

    return redirect(url_for("index.home"))


@users_bp.post("/check-email")
def check_email():
    """Check if an email is valid for registration.

    This endpoint checks:
    1. If the email is already registered (confirmed or unconfirmed)
    2. If the email's domain is blacklisted

    Example Request:

    .. json::

        {"email": "user@example.com"}

    Example Response:

    .. json::

        {
            "valid": boolean,
            "reason": "email_taken" | "domain_blacklisted" | null
        }
    """
    data = request.get_json()
    if not data or "email" not in data:
        return jsonify({"error": "Email is required"}), 400

    email, email_error = validate_registration_email(data["email"])
    if email_error in {"missing_email", "invalid_email"}:
        return jsonify({"error": "Invalid email format"}), 400

    if email_error == "domain_blacklisted":
        return jsonify({
            "valid": False,
            "reason": "domain_blacklisted"
        })

    if email_error == "email_taken":
        return jsonify({
            "valid": False,
            "reason": "email_taken"
        })

    return jsonify({"valid": True, "reason": None})


@users_bp.route("/resend-verification-email", methods=["POST"])
@login_required
def resend_verification_email():
    form = MeBFlaskForm()
    if form.validate_on_submit():
        if not current_user.unconfirmed_email:
            flash.info("There is no email address awaiting verification on your account.")
            return redirect(url_for("index.profile"))

        try:
            send_verification_email(
                current_user,
                "Please verify your email address",
                "email/user-email-address-verification.txt"
            )
        except Exception:
            current_app.logger.exception(
                "Error resending verification email for user %s", current_user.id
            )
            flash.error("The verification email could not be sent. Please try again later.")
        else:
            flash.success("Verification email sent!")
    return redirect(url_for("index.profile"))


@users_bp.route("/lost-username", methods=["GET", "POST"])
@login_forbidden
def lost_username():
    """ User's forgot username, request email with info endpoint. """
    form = ForgotUsernameForm()
    if form.validate_on_submit():
        user = User.get(email=form.email.data)
        if user is None:
            form.email.errors.append(f"The given email address ({form.email.data}) does not exist in our database.")
        else:
            try:
                send_forgot_username_email(user)
            except Exception:
                current_app.logger.exception(
                    "Error sending username recovery email for user %s", user.id
                )
                flash.error("The username recovery email could not be sent. Please try again later.")
            else:
                flash.success("Username recovery email sent!")
                return redirect(url_for("index.home"))

    form_errors = {k: ". ".join(v) for k, v in form.errors.items()}
    form_data = dict(**form.data)
    form_data.pop("csrf_token", None)

    return render_template("users/lost-username.html", props=json.dumps({
        "mtcaptcha_site_key": current_app.config.get("MTCAPTCHA_PUBLIC_KEY"),
        "csrf_token": generate_csrf(),
        "initial_form_data": form_data,
        "initial_errors": form_errors
    }))


@users_bp.route("/lost-password", methods=["GET", "POST"])
@login_forbidden
def lost_password():
    """ User's forgot password, request email to reset password endpoint. """
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.get(name=form.username.data, email=form.email.data)
        if user is None:
            form.email.errors.append(f"User with given username ({form.username.data}) and email ({form.email.data}) combination not found.")
        else:
            try:
                send_forgot_password_email(user)
            except Exception:
                current_app.logger.exception(
                    "Error sending password reset email for user %s", user.id
                )
                flash.error("The password reset email could not be sent. Please try again later.")
            else:
                flash.success("Password reset link sent!")
                return redirect(url_for("index.home"))

    form_errors = {k: ". ".join(v) for k, v in form.errors.items()}
    form_data = dict(**form.data)
    form_data.pop("csrf_token", None)

    return render_template("users/lost-password.html", props=json.dumps({
        "mtcaptcha_site_key": current_app.config.get("MTCAPTCHA_PUBLIC_KEY"),
        "csrf_token": generate_csrf(),
        "initial_form_data": form_data,
        "initial_errors": form_errors
    }))


@users_bp.route("/reset-password", methods=["GET", "POST"])
@login_forbidden
def reset_password():
    """ User"s reset password endpoint. """
    parsed_link = _parse_email_link_args()
    if parsed_link is None:
        flash.error("Unable to reset password.")
        return redirect(url_for("index.home"))

    user_id, timestamp, created_at = parsed_link
    if created_at + current_app.config["EMAIL_RESET_PASSWORD_EXPIRY"] <= datetime.now(timezone.utc):
        flash.error("Password reset link expired.")
        return redirect(url_for("index.home"))

    user = User.get(id=user_id)
    if user is None:
        flash.error("User not found.")
        return redirect(url_for("index.home"))

    received_checksum = request.args.get("checksum")
    # bound to the current password hash, so a used link no longer validates
    checksum = create_reset_password_checksum(user, timestamp)
    if not _checksum_matches(checksum, received_checksum):
        flash.error("Unable to reset password.")
        return redirect(url_for("index.home"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        db.session.commit()

        flash.success("Password reset!")
        return redirect(url_for("index.home"))

    form_errors = {k: ". ".join(v) for k, v in form.errors.items()}
    return render_template("users/reset-password.html", props=json.dumps({
        "csrf_token": generate_csrf(),
        "initial_errors": form_errors
    }))


@users_bp.route("/logout")
@login_required
def logout():
    # the remember cookie is cleared on logout, so clear our record of it as well
    current_user.update_remember_me(False)
    db.session.commit()
    logout_user()
    return redirect(url_for("index.home"))

import json
from datetime import datetime, timezone

from flask import Blueprint, current_app, redirect, render_template, request, url_for, jsonify
from flask_login import logout_user, login_required, login_user, current_user
from flask_wtf.csrf import generate_csrf
from sqlalchemy.exc import IntegrityError

from metabrainz import bcrypt, flash
from metabrainz.index.forms import MeBFlaskForm
from metabrainz.model import db
from metabrainz.model.user import User, UsernameNotAllowedException
from metabrainz.model.webhook import EVENT_USER_CREATED, EVENT_USER_UPDATED
from metabrainz.model.domain_blacklist import DomainBlacklist
from metabrainz.user import login_forbidden
from metabrainz.user.email import send_forgot_password_email, send_forgot_username_email, create_email_link_checksum, \
    VERIFY_EMAIL, RESET_PASSWORD, send_verification_email
from metabrainz.user.forms import UserLoginForm, UserSignupForm, ForgotPasswordForm, ForgotUsernameForm, \
    ResetPasswordForm
from metabrainz.user.rate_limit import check_signup_rate_limit, increment_signup_count

users_bp = Blueprint("users", __name__)


@users_bp.route("/signup", methods=["GET", "POST"])
@login_forbidden
def signup():
    """ User signup endpoint. """
    form = UserSignupForm()
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

                    send_verification_email(
                        user,
                        "Please verify your email address",
                        "email/user-email-address-verification.txt"
                    )
                    login_user(user)
                    flash.success("Account created. Please check your inbox to complete verification.")
                    redirect_to = request.args.get("next") or url_for("index.home")
                    return redirect(redirect_to)
                except UsernameNotAllowedException:
                    form.username.errors.append("Username is not allowed.")
                    db.session.rollback()
                except Exception as e:
                    flash.error(f"An unexpected error occurred: {e}")
                    current_app.logger.exception("Error creating user", exc_info=True)

    form_data = dict(**form.data)
    form_data.pop("csrf_token", None)

    return render_template("users/signup.html", props=json.dumps({
        "mtcaptcha_site_key": current_app.config.get("MTCAPTCHA_PUBLIC_KEY"),
        "csrf_token": generate_csrf(),
        "initial_form_data": form_data,
        "initial_errors": form.props_errors
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
                    db.session.commit()

                    flash.success("Logged in successfully.")
                    redirect_to = request.args.get("next")
                    if not redirect_to:
                        redirect_to = url_for("index.home")
                    return redirect(redirect_to)

    form_errors = {k: ". ".join(v) for k, v in form.errors.items()}
    form_data = dict(**form.data)
    form_data.pop("csrf_token", None)

    return render_template("users/login.html", props=json.dumps({
        "mtcaptcha_site_key": current_app.config.get("MTCAPTCHA_PUBLIC_KEY"),
        "csrf_token": generate_csrf(),
        "initial_form_data": form_data,
        "initial_errors": form_errors
    }))


@users_bp.route("/verify-email")
def verify_email():
    """ User"s email verification endpoint. """
    user_id = request.args.get("user_id")
    timestamp = int(request.args.get("timestamp"))
    if datetime.fromtimestamp(timestamp) + current_app.config["EMAIL_VERIFICATION_EXPIRY"] <= datetime.now():
        flash.error("Email verification link expired.")
        return redirect(url_for("index.home"))

    received_checksum = request.args.get("checksum")

    user = User.get(id=user_id)
    if user is None:
        flash.error("User not found.")
        return redirect(url_for("index.home"))

    checksum = create_email_link_checksum(VERIFY_EMAIL, user.id, user.unconfirmed_email, timestamp)
    if checksum != received_checksum:
        flash.error("Unable to verify email.")
        return redirect(url_for("index.home"))

    try:
        old_email = user.email
        user.email = user.unconfirmed_email
        user.unconfirmed_email = None
        user.email_confirmed_at = datetime.now(tz=timezone.utc)
        db.session.commit()

        user.emit_event(
            EVENT_USER_UPDATED,
            old={"email": old_email},
            new={"email": user.email},
        )

        flash.success("Email verified!")
    except IntegrityError:
        flash.error(f"The email is already associated with an another account.")
        db.session.rollback()

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

    email = data["email"].strip().lower()

    if not email or '@' not in email:
        return jsonify({"error": "Invalid email format"}), 400

    if DomainBlacklist.is_email_blacklisted(email):
        return jsonify({
            "valid": False,
            "reason": "domain_blacklisted"
        })

    existing_user = User.get(email=email)
    if existing_user is not None:
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
        send_verification_email(
            current_user,
            "Please verify your email address",
            "email/user-email-address-verification.txt"
        )
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
            send_forgot_username_email(user)
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
            send_forgot_password_email(user)
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
    user_id = request.args.get("user_id")

    timestamp = int(request.args.get("timestamp"))
    if datetime.fromtimestamp(timestamp) + current_app.config["EMAIL_RESET_PASSWORD_EXPIRY"] <= datetime.now():
        flash.error("Password reset link expired.")
        return redirect(url_for("index.home"))

    user = User.get(id=user_id)
    if user is None:
        flash.error("User not found.")
        return redirect(url_for("index.home"))

    received_checksum = request.args.get("checksum")
    checksum = create_email_link_checksum(RESET_PASSWORD, user.id, user.get_email_any(), timestamp)
    if checksum != received_checksum:
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
    logout_user()
    return redirect(url_for("index.home"))

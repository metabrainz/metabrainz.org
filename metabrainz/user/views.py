from datetime import datetime, timezone

from flask import Blueprint, current_app, redirect, render_template, request, url_for
from flask_login import logout_user, login_required, login_user, current_user

from metabrainz import bcrypt, flash
from metabrainz.model import db
from metabrainz.model.user import User
from metabrainz.user import login_forbidden
from metabrainz.user.email import send_forgot_password_email, send_forgot_username_email, create_email_link_checksum, \
    VERIFY_EMAIL, RESET_PASSWORD, send_verification_email
from metabrainz.user.forms import UserLoginForm, UserSignupForm, ForgotPasswordForm, ForgotUsernameForm, \
    ResetPasswordForm, UserEditForm

users_bp = Blueprint("users", __name__)


@users_bp.route("/signup", methods=["GET", "POST"])
@login_forbidden
def signup():
    """ User signup endpoint. """
    form = UserSignupForm()
    if form.validate_on_submit():
        user = User.get(name=form.username.data)
        if user is not None:
            form.form_errors.append(f"Another user with username '{form.username.data}' exists.")
            return render_template("users/signup.html", form=form)

        # TODO: Handle the case where multiple users sign up with same email but haven"t verified it yet
        user = User.get(email=form.email.data)
        if user is not None:
            form.form_errors.append(f"Another user with email '{form.email.data}' exists.")
            return render_template("users/signup.html", form=form)

        user = User.add(name=form.username.data, email=form.email.data, password=form.password.data)
        send_verification_email(
            user,
            "Please verify your email address",
            "email/user-email-address-verification.txt"
        )
        login_user(user)
        flash.success("Account created. Please check your inbox to complete verification.")
        return redirect(url_for("index.home"))

    return render_template("users/signup.html", form=form)


@users_bp.route("/login", methods=["GET", "POST"])
@login_forbidden
def login():
    """ User login endpoint. """
    form = UserLoginForm()
    if form.validate_on_submit():
        user = User.get(name=form.username.data)
        if user is None:
            form.form_errors.append(f"Username {form.username.data} not found.")
            return render_template("users/login.html", form=form)
        
        if not bcrypt.check_password_hash(user.password, form.password.data):
            form.form_errors.append("Invalid username or password.")
            return render_template("users/login.html", form=form)

        login_user(user, remember=form.remember_me.data)
        flash.success("Logged in successfully.")
        return redirect(url_for("index.home"))

    return render_template("users/login.html", form=form)


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

    checksum = create_email_link_checksum(VERIFY_EMAIL, user, timestamp)
    if checksum != received_checksum:
        flash.error("Unable to verify email.")
        return redirect(url_for("index.home"))

    user.email_confirmed_at = datetime.now(tz=timezone.utc)
    db.session.commit()

    flash.success("Email verified!")
    return redirect(url_for("index.home"))


@users_bp.route('/users/profile')
@login_required
def profile():
    return render_template("users/profile.html")


@users_bp.route('/users/profile/edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    form = UserEditForm()
    if form.validate_on_submit():
        current_user.update(email=form.email.data)
        send_verification_email(
            current_user,
            "Please verify your email address",
            "email/user-email-address-verification.txt"
        )
        flash.success("Profile updated.")
        return redirect(url_for(".profile"))

    form.email.data = current_user.email
    return render_template('users/profile-edit.html', form=form)


# TODO: Add email verification resend
@users_bp.route("/lost-username", methods=["GET", "POST"])
@login_forbidden
def lost_username():
    """ User's forgot username, request email with info endpoint. """
    form = ForgotUsernameForm()
    if form.validate_on_submit():
        user = User.get(email=form.email.data)
        if user is None:
            form.form_errors.append(f"The given email address ({form.email.data}) does not exist in our database.")
            return render_template("users/lost_username.html", form=form)

        send_forgot_username_email(user)
        flash.success("Username recovery link sent!")
        return redirect(url_for("index.home"))

    return render_template("users/lost_username.html", form=form)


@users_bp.route("/lost-password", methods=["GET", "POST"])
@login_forbidden
def lost_password():
    """ User"s forgot password, request email to reset endpoint. """
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.get(name=form.username.data, email=form.email.data)
        if user is None:
            form.form_errors.append(f"User with given username ({form.username.data}) and email ({form.email.data}) combination not found.")
            return render_template("users/lost_password.html", form=form)

        send_forgot_password_email(user)
        flash.success("Password reset link sent!")
        return redirect(url_for("index.home"))

    return render_template("users/lost_password.html", form=form)


@users_bp.route("/reset-password", methods=["GET", "POST"])
@login_forbidden
def reset_password():
    """ User"s reset password endpoint. """
    user_id = request.args.get("user_id")

    timestamp = int(request.args.get("timestamp"))
    if datetime.fromtimestamp(timestamp) + current_app.config["EMAIL_RESET_PASSWORD_EXPIRY"] <= datetime.now():
        flash.error("Email verification link expired.")
        return redirect(url_for("index.home"))

    received_checksum = request.args.get("checksum")

    user = User.get(id=user_id)
    if user is None:
        flash.error("User not found.")
        return redirect(url_for("index.home"))

    checksum = create_email_link_checksum(RESET_PASSWORD, user, timestamp)
    if checksum != received_checksum:
        flash.error("Unable to reset password.")
        return redirect(url_for("index.home"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        db.session.commit()

        flash.success("Password reset!")
        return redirect(url_for("index.home"))

    return render_template("users/reset_password.html", form=form)


@users_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index.home"))

"""WTForms definitions (CSRF protection comes from Flask-WTF)."""

import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

PASSWORD_RULES = (
    "Use at least 10 characters including a letter and a number."
)


def strong_password(_form, field):
    value = field.data or ""
    if len(value) < 10:
        raise ValidationError(PASSWORD_RULES)
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValidationError(PASSWORD_RULES)


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), strong_password])
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", "Passwords do not match.")],
    )
    submit = SubmitField("Create account")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Keep me signed in")
    submit = SubmitField("Sign in")


class ResendVerificationForm(FlaskForm):
    submit = SubmitField("Resend verification email")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    password = PasswordField("New password", validators=[DataRequired(), strong_password])
    confirm_password = PasswordField(
        "Confirm new password",
        validators=[DataRequired(), EqualTo("password", "Passwords do not match.")],
    )
    submit = SubmitField("Update password")


class EmptyForm(FlaskForm):
    submit = SubmitField("Confirm")

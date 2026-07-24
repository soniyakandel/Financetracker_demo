from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp

from app.security.policy import StrongPassword


class ProfileForm(FlaskForm):
    name = StringField(
        "Full name",
        validators=[
            DataRequired(message="Please enter your name."),
            Length(min=2, max=80),
            Regexp(
                r"^[A-Za-z][A-Za-z .'-]*$",
                message="Use letters, spaces, apostrophes or hyphens only.",
            ),
        ],
    )
    email = StringField(
        "Email address",
        validators=[DataRequired(), Email(), Length(max=120)],
    )
    submit = SubmitField("Save changes")


class ChangePasswordForm(FlaskForm):

    current_password = PasswordField(
        "Current password",
        validators=[DataRequired(message="Please enter your current password.")],
    )
    new_password = PasswordField(
        "New password",
        validators=[DataRequired(message="Please choose a new password."), StrongPassword()],
    )
    confirm_password = PasswordField(
        "Confirm new password",
        validators=[
            DataRequired(message="Please type the new password again."),
            EqualTo("new_password", message="The two passwords do not match."),
        ],
    )
    submit = SubmitField("Change password")

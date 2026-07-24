from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp

from app.security.policy import StrongPassword


class RegisterForm(FlaskForm):
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
        validators=[
            DataRequired(message="Please enter your email address."),
            Email(message="That does not look like a valid email address."),
            Length(max=120),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Please choose a password."), StrongPassword()],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(message="Please type the password again."),
            EqualTo("password", message="The two passwords do not match."),
        ],
    )
    accept_terms = BooleanField(
        "I understand this is a student project and will not store real bank details.",
        validators=[DataRequired(message="Please tick the box to continue.")],
    )
    submit = SubmitField("Create account")


class LoginForm(FlaskForm):
    email = StringField(
        "Email address",
        validators=[DataRequired(), Email(), Length(max=120)],
    )
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Keep me signed in on this device")
    submit = SubmitField("Sign in")


class OtpForm(FlaskForm):
    code = StringField(
        "Six digit code",
        validators=[
            DataRequired(message="Please enter the code we sent you."),
            Regexp(r"^\d{6}$", message="The code is exactly six digits."),
        ],
    )
    submit = SubmitField("Verify and continue")

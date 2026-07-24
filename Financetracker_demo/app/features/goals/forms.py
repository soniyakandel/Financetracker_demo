from datetime import date

from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, StringField, SubmitField
from wtforms.validators import (
    DataRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)


class GoalForm(FlaskForm):
    title = StringField(
        "What are you saving for?",
        validators=[
            DataRequired(message="Please name your goal."),
            Length(min=2, max=100),
        ],
    )
    target_amount = DecimalField(
        "Target amount",
        places=2,
        validators=[
            DataRequired(message="Please enter a target."),
            NumberRange(min=1, max=10_000_000, message="Enter a sensible target."),
        ],
    )
    target_date = DateField("Target date", validators=[Optional()])
    note = StringField("Note", validators=[Optional(), Length(max=200)])
    submit = SubmitField("Save goal")

    def validate_target_date(self, field):
        if field.data and field.data < date.today():
            raise ValidationError("Pick a date in the future.")


class ContributionForm(FlaskForm):
    amount = DecimalField(
        "Amount to add",
        places=2,
        validators=[
            DataRequired(message="Please enter an amount."),
            NumberRange(min=0.01, max=10_000_000, message="Enter a sensible amount."),
        ],
    )
    added_on = DateField("Date", default=date.today, validators=[DataRequired()])
    note = StringField("Note", validators=[Optional(), Length(max=200)])
    submit = SubmitField("Add to goal")

from datetime import date

from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange

from app.models.recurring import MONTHLY, WEEKLY


class RecurringForm(FlaskForm):
    title = StringField(
        "What is it for?",
        validators=[
            DataRequired(message="Please name this recurring expense."),
            Length(min=2, max=100),
        ],
    )
    amount = DecimalField(
        "Amount each time",
        places=2,
        validators=[
            DataRequired(message="Please enter an amount."),
            NumberRange(min=0.01, max=10_000_000, message="Enter a sensible amount."),
        ],
    )
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    frequency = SelectField(
        "How often?",
        choices=[(MONTHLY, "Every month"), (WEEKLY, "Every week")],
        default=MONTHLY,
    )
    start_on = DateField(
        "First due on",
        default=date.today,
        validators=[DataRequired(message="Please choose the first due date.")],
    )
    submit = SubmitField("Save recurring expense")

    def set_category_choices(self, categories):
        self.category_id.choices = [(c.id, f"{c.icon} {c.name}") for c in categories]

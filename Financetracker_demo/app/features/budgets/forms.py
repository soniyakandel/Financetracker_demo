from datetime import date

from flask_wtf import FlaskForm
from wtforms import DecimalField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Regexp


def month_choices(count=12):
    today = date.today()
    choices = []
    for offset in range(count):
        month_index = today.month - 1 + offset
        year = today.year + month_index // 12
        month = month_index % 12 + 1
        key = f"{year:04d}-{month:02d}"
        choices.append((key, date(year, month, 1).strftime("%B %Y")))
    return choices


class BudgetForm(FlaskForm):
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    month = SelectField(
        "Month",
        validators=[
            DataRequired(),
            Regexp(r"^\d{4}-\d{2}$", message="Choose a valid month."),
        ],
    )
    amount_limit = DecimalField(
        "Monthly limit",
        places=2,
        validators=[
            DataRequired(message="Please enter a limit."),
            NumberRange(min=1, max=10_000_000, message="Enter a sensible limit."),
        ],
    )
    submit = SubmitField("Save budget")

    def set_choices(self, categories):
        self.category_id.choices = [(c.id, f"{c.icon} {c.name}") for c in categories]
        self.month.choices = month_choices()

from datetime import date

from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from app.models.transaction import EXPENSE, INCOME

MAX_AMOUNT = 10_000_000


class TransactionForm(FlaskForm):

    type = SelectField(
        "Type",
        choices=[(EXPENSE, "Expense (money out)"), (INCOME, "Income (money in)")],
        default=EXPENSE,
    )
    amount = DecimalField(
        "Amount",
        places=2,
        validators=[
            DataRequired(message="Please enter an amount."),
            NumberRange(
                min=0.01,
                max=MAX_AMOUNT,
                message="Enter an amount between 0.01 and 10,000,000.",
            ),
        ],
    )
    category_id = SelectField("Category", coerce=int, validators=[Optional()])
    spent_on = DateField(
        "Date",
        default=date.today,
        validators=[DataRequired(message="Please choose a date.")],
    )
    note = StringField("Note", validators=[Optional(), Length(max=200)])
    submit = SubmitField("Save transaction")

    def set_category_choices(self, categories):
        self.category_id.choices = [(0, "- none -")] + [
            (c.id, f"{c.icon} {c.name}") for c in categories
        ]

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators=extra_validators):
            return False

        if self.type.data == EXPENSE and not self.category_id.data:
            self.category_id.errors.append("Please choose a category for an expense.")
            return False

        if self.spent_on.data and self.spent_on.data > date.today():
            self.spent_on.errors.append("The date cannot be in the future.")
            return False

        return True

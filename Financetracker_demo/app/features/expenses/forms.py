from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange


class ExpenseForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=100)])
    amount = DecimalField(
        "Amount", places=2, validators=[DataRequired(), NumberRange(min=0.01)]
    )
    date = DateField("Date", validators=[DataRequired()])
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Save")

    def set_category_choices(self, categories):
        self.category_id.choices = [(c.id, c.icon + " " + c.name) for c in categories]

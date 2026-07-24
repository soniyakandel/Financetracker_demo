from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp

COLOUR_CHOICES = [
    ("#ef4444", "Red"),
    ("#f97316", "Orange"),
    ("#eab308", "Yellow"),
    ("#22c55e", "Green"),
    ("#14b8a6", "Teal"),
    ("#3b82f6", "Blue"),
    ("#6366f1", "Indigo"),
    ("#a855f7", "Purple"),
    ("#ec4899", "Pink"),
    ("#64748b", "Grey"),
]

ICON_CHOICES = [
    ("📌", "Pin"), ("🍔", "Food"), ("🚌", "Transport"), ("🛍️", "Shopping"),
    ("🎬", "Entertainment"), ("💡", "Bills"), ("🏥", "Health"), ("📚", "Education"),
    ("🏠", "Home"), ("✈️", "Travel"), ("🎁", "Gifts"), ("🐾", "Pets"),
    ("💻", "Tech"), ("💪", "Fitness"), ("☕", "Coffee"),
]


class CategoryForm(FlaskForm):
    name = StringField(
        "Category name",
        validators=[
            DataRequired(message="Please give the category a name."),
            Length(min=2, max=50),
            Regexp(
                r"^[A-Za-z0-9][A-Za-z0-9 &'/-]*$",
                message="Use letters, numbers, spaces and & ' / - only.",
            ),
        ],
    )
    icon = SelectField("Icon", choices=ICON_CHOICES, default="📌")
    colour = SelectField("Colour", choices=COLOUR_CHOICES, default="#64748b")
    submit = SubmitField("Save category")

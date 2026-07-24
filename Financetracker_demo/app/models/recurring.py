from datetime import timedelta

from app.extensions import db
from app.models.base import utcnow

WEEKLY = "weekly"
MONTHLY = "monthly"
FREQUENCIES = (WEEKLY, MONTHLY)
FREQUENCY_LABELS = {WEEKLY: "Every week", MONTHLY: "Every month"}


def add_months(date_value, months=1):
    month_index = date_value.month - 1 + months
    year = date_value.year + month_index // 12
    month = month_index % 12 + 1

    if month == 12:
        first_of_next = date_value.replace(year=year + 1, month=1, day=1)
    else:
        first_of_next = date_value.replace(year=year, month=month + 1, day=1)
    last_day = (first_of_next - timedelta(days=1)).day

    return date_value.replace(year=year, month=month, day=min(date_value.day, last_day))


class RecurringExpense(db.Model):
    __tablename__ = "recurring_expenses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)

    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    frequency = db.Column(db.String(10), default=MONTHLY, nullable=False)

    start_on = db.Column(db.Date, nullable=False)
    next_due_on = db.Column(db.Date, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship(
        "User",
        backref=db.backref(
            "recurring_expenses", lazy="dynamic", cascade="all, delete-orphan"
        ),
    )
    category = db.relationship("Category")

    def advance(self):
        if self.frequency == WEEKLY:
            self.next_due_on = self.next_due_on + timedelta(days=7)
        else:
            self.next_due_on = add_months(self.next_due_on, 1)

    @property
    def frequency_label(self):
        return FREQUENCY_LABELS.get(self.frequency, self.frequency)

    def __repr__(self):
        return f"<RecurringExpense {self.title} {self.frequency}>"

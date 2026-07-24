from app.extensions import db
from app.models.base import utcnow

EXPENSE = "expense"
INCOME = "income"
TRANSACTION_TYPES = (EXPENSE, INCOME)


class Transaction(db.Model):

    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)

    type = db.Column(db.String(10), default=EXPENSE, nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    note = db.Column(db.String(200))
    spent_on = db.Column(db.Date, nullable=False, index=True)

    is_auto_generated = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = db.relationship(
        "User",
        backref=db.backref(
            "transactions", lazy="dynamic", cascade="all, delete-orphan"
        ),
    )
    category = db.relationship("Category", backref=db.backref("transactions"))

    @property
    def is_expense(self):
        return self.type == EXPENSE

    @property
    def signed_amount(self):
        return self.amount if self.type == INCOME else -self.amount

    def __repr__(self):
        return f"<Transaction {self.type} {self.amount} on {self.spent_on}>"

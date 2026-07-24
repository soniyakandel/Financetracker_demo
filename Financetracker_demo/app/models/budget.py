from decimal import Decimal

from app.extensions import db
from app.models.base import utcnow


class Budget(db.Model):

    __tablename__ = "budgets"
    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "category_id", "month", name="uq_budget_user_category_month"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)

    month = db.Column(db.String(7), nullable=False, index=True)
    amount_limit = db.Column(db.Numeric(12, 2), nullable=False)

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship(
        "User",
        backref=db.backref("budgets", lazy="dynamic", cascade="all, delete-orphan"),
    )
    category = db.relationship("Category")

    spent = Decimal("0.00")

    @property
    def remaining(self):
        return Decimal(self.amount_limit) - Decimal(self.spent)

    @property
    def percent_used(self):
        limit = Decimal(self.amount_limit)
        if limit <= 0:
            return 0
        return int(min(Decimal(self.spent) / limit * 100, 999))

    @property
    def status(self):
        used = self.percent_used
        if used >= 100:
            return "over"
        if used >= 80:
            return "warning"
        return "ok"

    def __repr__(self):
        return f"<Budget {self.month} category={self.category_id}>"

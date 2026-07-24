from decimal import Decimal

from app.extensions import db
from app.models.base import utcnow


class SavingsGoal(db.Model):
    __tablename__ = "savings_goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    title = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Numeric(12, 2), nullable=False)
    target_date = db.Column(db.Date, nullable=True)
    note = db.Column(db.String(200))

    is_achieved = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship(
        "User",
        backref=db.backref("goals", lazy="dynamic", cascade="all, delete-orphan"),
    )

    @property
    def saved_amount(self):
        return sum(
            (Decimal(c.amount) for c in self.contributions), Decimal("0.00")
        )

    @property
    def remaining_amount(self):
        left = Decimal(self.target_amount) - self.saved_amount
        return left if left > 0 else Decimal("0.00")

    @property
    def percent_complete(self):
        target = Decimal(self.target_amount)
        if target <= 0:
            return 0
        return int(min(self.saved_amount / target * 100, 100))

    def refresh_status(self):
        self.is_achieved = self.saved_amount >= Decimal(self.target_amount)

    def __repr__(self):
        return f"<SavingsGoal {self.title}>"


class GoalContribution(db.Model):
    __tablename__ = "goal_contributions"

    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(
        db.Integer, db.ForeignKey("savings_goals.id"), nullable=False, index=True
    )
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    note = db.Column(db.String(200))
    added_on = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    goal = db.relationship(
        "SavingsGoal",
        backref=db.backref(
            "contributions",
            lazy="select",
            cascade="all, delete-orphan",
            order_by="GoalContribution.added_on.desc()",
        ),
    )

    def __repr__(self):
        return f"<GoalContribution {self.amount} -> goal {self.goal_id}>"

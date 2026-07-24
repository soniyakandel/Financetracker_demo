from datetime import date

from app.extensions import db
from app.models.recurring import RecurringExpense
from app.models.transaction import EXPENSE, Transaction

MAX_ENTRIES_PER_RULE = 24


def generate_due_for(user, today=None):
    today = today or date.today()

    rules = RecurringExpense.query.filter_by(user_id=user.id, is_active=True).all()
    created = 0

    for rule in rules:
        made_for_this_rule = 0

        while rule.next_due_on <= today and made_for_this_rule < MAX_ENTRIES_PER_RULE:
            db.session.add(
                Transaction(
                    user_id=user.id,
                    category_id=rule.category_id,
                    type=EXPENSE,
                    amount=rule.amount,
                    note=rule.title,
                    spent_on=rule.next_due_on,
                    is_auto_generated=True,
                )
            )
            rule.advance()
            made_for_this_rule += 1
            created += 1

    if created:
        db.session.commit()

    return created

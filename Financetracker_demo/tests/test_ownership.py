from datetime import date

import pytest

from app.extensions import db
from app.models.budget import Budget
from app.models.category import Category
from app.models.goal import SavingsGoal
from app.models.recurring import RecurringExpense
from app.models.transaction import Transaction
from tests.conftest import sign_in


@pytest.fixture
def other_users_records(app, make_user):
    other_id = make_user(email="other@example.com", name="Other Person")

    with app.app_context():
        category = Category.query.filter_by(user_id=other_id).first()
        transaction = Transaction(
            user_id=other_id, type="expense", amount=999,
            category_id=category.id, spent_on=date.today(), note="Private",
        )
        rule = RecurringExpense(
            user_id=other_id, category_id=category.id, title="Their rent",
            amount=1000, frequency="monthly",
            start_on=date.today(), next_due_on=date.today(),
        )
        budget = Budget(
            user_id=other_id, category_id=category.id,
            month=date.today().strftime("%Y-%m"), amount_limit=5000,
        )
        goal = SavingsGoal(user_id=other_id, title="Their goal", target_amount=1000)
        db.session.add_all([transaction, rule, budget, goal])
        db.session.commit()

        return {
            "category": category.id,
            "transaction": transaction.id,
            "recurring": rule.id,
            "budget": budget.id,
            "goal": goal.id,
        }


def test_other_users_records_are_not_listed(app, user_id, other_users_records):
    client = sign_in(app)
    assert b"Private" not in client.get("/expenses/").data
    assert b"Their rent" not in client.get("/recurring/").data
    assert b"Their goal" not in client.get("/goals/").data


@pytest.mark.parametrize(
    "url_template, key",
    [
        ("/expenses/{}/edit", "transaction"),
        ("/categories/{}/edit", "category"),
        ("/recurring/{}/edit", "recurring"),
        ("/budgets/{}/edit", "budget"),
        ("/goals/{}/edit", "goal"),
    ],
)
def test_editing_another_users_record_is_refused(
    app, user_id, other_users_records, url_template, key
):
    client = sign_in(app)
    response = client.get(url_template.format(other_users_records[key]))
    assert response.status_code == 404


@pytest.mark.parametrize(
    "url_template, key",
    [
        ("/expenses/{}/delete", "transaction"),
        ("/categories/{}/delete", "category"),
        ("/recurring/{}/delete", "recurring"),
        ("/budgets/{}/delete", "budget"),
        ("/goals/{}/delete", "goal"),
    ],
)
def test_deleting_another_users_record_is_refused(
    app, user_id, other_users_records, url_template, key
):
    client = sign_in(app)
    assert client.post(url_template.format(other_users_records[key])).status_code == 404


def test_another_users_records_survive_the_attempt(app, user_id, other_users_records):
    client = sign_in(app)
    client.post(f"/expenses/{other_users_records['transaction']}/delete")
    client.post(f"/goals/{other_users_records['goal']}/delete")

    with app.app_context():
        assert db.session.get(Transaction, other_users_records["transaction"]) is not None
        assert db.session.get(SavingsGoal, other_users_records["goal"]) is not None


def test_a_transaction_cannot_be_filed_under_another_users_category(
    app, user_id, other_users_records
):
    client = sign_in(app)
    client.post(
        "/expenses/new",
        data={
            "type": "expense",
            "amount": "50",
            "category_id": other_users_records["category"],
            "spent_on": date.today().isoformat(),
        },
    )

    with app.app_context():
        assert Transaction.query.filter_by(user_id=user_id).count() == 0


def test_pages_require_a_signed_in_user(app):
    guest = app.test_client()
    for path in ("/dashboard/", "/expenses/", "/budgets/", "/goals/",
                 "/profile/", "/profile/sessions", "/profile/activity"):
        assert guest.get(path).status_code == 302, path

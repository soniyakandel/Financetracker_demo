from datetime import date, timedelta

from app.extensions import db
from app.models.budget import Budget
from app.models.category import Category
from app.models.goal import SavingsGoal
from app.models.recurring import RecurringExpense, add_months
from app.models.transaction import Transaction
from tests.conftest import sign_in


def category_id_for(app, user_id, name="Food"):
    with app.app_context():
        return Category.query.filter_by(user_id=user_id, name=name).first().id


def test_an_expense_can_be_added_edited_and_deleted(app, user_id):
    client = sign_in(app)
    food = category_id_for(app, user_id)

    client.post("/expenses/new", data={
        "type": "expense", "amount": "250.50", "category_id": food,
        "spent_on": date.today().isoformat(), "note": "Lunch",
    })
    with app.app_context():
        transaction = Transaction.query.one()
        assert str(transaction.amount) == "250.50"
        transaction_id = transaction.id

    client.post(f"/expenses/{transaction_id}/edit", data={
        "type": "expense", "amount": "300.00", "category_id": food,
        "spent_on": date.today().isoformat(), "note": "Lunch and coffee",
    })
    with app.app_context():
        assert str(db.session.get(Transaction, transaction_id).amount) == "300.00"

    client.post(f"/expenses/{transaction_id}/delete")
    with app.app_context():
        assert db.session.get(Transaction, transaction_id) is None


def test_an_expense_needs_a_category_but_income_does_not(app, user_id):
    client = sign_in(app)

    response = client.post("/expenses/new", data={
        "type": "expense", "amount": "100", "category_id": 0,
        "spent_on": date.today().isoformat(),
    })
    assert b"choose a category" in response.data

    client.post("/expenses/new", data={
        "type": "income", "amount": "5000", "category_id": 0,
        "spent_on": date.today().isoformat(), "note": "Salary",
    })
    with app.app_context():
        assert Transaction.query.filter_by(type="income").count() == 1


def test_a_future_dated_expense_is_refused(app, user_id):
    client = sign_in(app)
    food = category_id_for(app, user_id)

    response = client.post("/expenses/new", data={
        "type": "expense", "amount": "100", "category_id": food,
        "spent_on": (date.today() + timedelta(days=1)).isoformat(),
    })
    assert b"cannot be in the future" in response.data


def test_filters_narrow_the_history(app, user_id):
    client = sign_in(app)
    food = category_id_for(app, user_id)
    rent = category_id_for(app, user_id, "Rent")

    with app.app_context():
        db.session.add_all([
            Transaction(user_id=user_id, type="expense", amount=100,
                        category_id=food, spent_on=date(2026, 1, 5), note="old lunch"),
            Transaction(user_id=user_id, type="expense", amount=12000,
                        category_id=rent, spent_on=date(2026, 6, 1), note="rent"),
            Transaction(user_id=user_id, type="income", amount=50000,
                        spent_on=date(2026, 6, 1), note="salary"),
        ])
        db.session.commit()

    assert b"old lunch" in client.get(f"/expenses/?category={food}").data
    assert b"rent" not in client.get(f"/expenses/?category={food}").data
    assert b"salary" in client.get("/expenses/?type=income").data
    assert b"old lunch" not in client.get("/expenses/?start=2026-05-01").data
    assert b"salary" in client.get("/expenses/?search=sala").data


def test_budget_progress_and_over_budget_state(app, user_id):
    client = sign_in(app)
    food = category_id_for(app, user_id)
    month = date.today().strftime("%Y-%m")

    client.post("/budgets/new", data={
        "category_id": food, "month": month, "amount_limit": "1000",
    })
    with app.app_context():
        db.session.add(Transaction(user_id=user_id, type="expense", amount=900,
                                   category_id=food, spent_on=date.today()))
        db.session.commit()

    assert b"Nearly there" in client.get("/budgets/").data

    with app.app_context():
        db.session.add(Transaction(user_id=user_id, type="expense", amount=400,
                                   category_id=food, spent_on=date.today()))
        db.session.commit()

    body = client.get("/budgets/").get_data(as_text=True)
    assert "Over budget" in body
    with app.app_context():
        budget = Budget.query.one()
        budget.spent = 1300
        assert budget.percent_used == 130
        assert budget.status == "over"


def test_a_goal_is_marked_achieved_once_the_target_is_reached(app, user_id):
    client = sign_in(app)
    client.post("/goals/new", data={"title": "Laptop", "target_amount": "1000"})

    with app.app_context():
        goal_id = SavingsGoal.query.one().id

    client.post(f"/goals/{goal_id}/contribute",
                data={"amount": "400", "added_on": date.today().isoformat()})
    with app.app_context():
        goal = db.session.get(SavingsGoal, goal_id)
        assert goal.percent_complete == 40
        assert not goal.is_achieved

    client.post(f"/goals/{goal_id}/contribute",
                data={"amount": "600", "added_on": date.today().isoformat()})
    with app.app_context():
        goal = db.session.get(SavingsGoal, goal_id)
        assert goal.is_achieved
        assert goal.remaining_amount == 0


def test_add_months_clamps_to_the_end_of_a_short_month():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert add_months(date(2026, 12, 15), 1) == date(2027, 1, 15)


def test_due_recurring_expenses_are_created_once_at_sign_in(app, user_id):
    rent = category_id_for(app, user_id, "Rent")
    start = date.today().replace(day=1) - timedelta(days=90)

    with app.app_context():
        db.session.add(RecurringExpense(
            user_id=user_id, category_id=rent, title="Room rent", amount=12000,
            frequency="monthly", start_on=start, next_due_on=start,
        ))
        db.session.commit()

    sign_in(app)
    with app.app_context():
        created = Transaction.query.filter_by(is_auto_generated=True).count()
        assert created >= 3
        assert RecurringExpense.query.one().next_due_on > date.today()

    sign_in(app)
    with app.app_context():
        assert Transaction.query.filter_by(is_auto_generated=True).count() == created


def test_a_paused_rule_creates_nothing(app, user_id):
    rent = category_id_for(app, user_id, "Rent")
    with app.app_context():
        db.session.add(RecurringExpense(
            user_id=user_id, category_id=rent, title="Paused rent", amount=1000,
            frequency="monthly", start_on=date.today() - timedelta(days=60),
            next_due_on=date.today() - timedelta(days=60), is_active=False,
        ))
        db.session.commit()

    sign_in(app)
    with app.app_context():
        assert Transaction.query.count() == 0


def test_default_categories_cannot_be_deleted(app, user_id):
    client = sign_in(app)
    food = category_id_for(app, user_id)

    response = client.post(f"/categories/{food}/delete", follow_redirects=True)
    assert b"cannot be deleted" in response.data
    with app.app_context():
        assert db.session.get(Category, food) is not None


def test_a_category_in_use_cannot_be_deleted(app, user_id):
    client = sign_in(app)
    client.post("/categories/new", data={"name": "Gym", "icon": "💪", "colour": "#22c55e"})

    with app.app_context():
        gym = Category.query.filter_by(user_id=user_id, name="Gym").one()
        gym_id = gym.id
        db.session.add(Transaction(user_id=user_id, type="expense", amount=500,
                                   category_id=gym_id, spent_on=date.today()))
        db.session.commit()

    response = client.post(f"/categories/{gym_id}/delete", follow_redirects=True)
    assert b"cannot be deleted" in response.data
    with app.app_context():
        assert db.session.get(Category, gym_id) is not None


def test_the_dashboard_totals_match_the_transactions(app, user_id):
    client = sign_in(app)
    food = category_id_for(app, user_id)

    with app.app_context():
        db.session.add_all([
            Transaction(user_id=user_id, type="income", amount=60000, spent_on=date.today()),
            Transaction(user_id=user_id, type="expense", amount=15000,
                        category_id=food, spent_on=date.today()),
        ])
        db.session.commit()

    body = client.get("/dashboard/").get_data(as_text=True)
    assert "60,000.00" in body
    assert "15,000.00" in body
    assert "45,000.00" in body

    breakdown = client.get("/dashboard/api/category-breakdown").get_json()
    assert breakdown["values"] == [15000.0]
    trend = client.get("/dashboard/api/monthly-trend").get_json()
    assert trend["income"][-1] == 60000.0

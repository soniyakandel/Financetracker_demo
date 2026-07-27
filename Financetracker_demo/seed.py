import random
from datetime import date, timedelta
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models.budget import Budget
from app.models.category import Category
from app.models.goal import GoalContribution, SavingsGoal
from app.models.recurring import MONTHLY, WEEKLY, RecurringExpense
from app.models.transaction import EXPENSE, INCOME, Transaction
from app.models.user import User

DEMO_EMAIL = "demo@financetracker.app"
DEMO_PASSWORD = "Demo@2026Pass"

SPENDING_PATTERN = [
    ("Food",              ["Groceries", "Lunch at college", "Dinner out", "Snacks"],       150,  1800, 8),
    ("Transport",         ["Bus fare", "Taxi", "Fuel", "Bike service"],                     50,   900, 5),
    ("Shopping",          ["T-shirt", "Shoes", "Stationery"],                              400,  3500, 2),
    ("Entertainment",     ["Cinema ticket", "Music subscription", "Concert"],              200,  1500, 2),
    ("Bills & Utilities", ["Electricity", "Water", "Internet top-up"],                     600,  2500, 2),
    ("Health & Medical",  ["Pharmacy", "Doctor visit"],                                    300,  2000, 1),
    ("Education",         ["Textbook", "Online course", "Printing"],                       500,  3000, 1),
    ("Travel",            ["Bus to home town", "Weekend trip"],                           1000,  5000, 1),
]


def money(low, high):
    return Decimal(random.randrange(low, high, 10))


def clear_demo_account():
    existing = User.query.filter_by(email=DEMO_EMAIL).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()


def build_demo_account():
    user = User(name="Demo Student", email=DEMO_EMAIL)
    user.set_password(DEMO_PASSWORD)
    db.session.add(user)
    db.session.flush()

    Category.create_defaults_for(user)
    db.session.flush()

    categories = {c.name: c for c in user.categories}
    today = date.today()

    for months_back in range(5, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=months_back * 30)).replace(day=1)

        db.session.add(
            Transaction(
                user_id=user.id,
                type=INCOME,
                amount=Decimal("55000") + Decimal(random.randrange(0, 8000, 500)),
                note="Monthly allowance and part-time work",
                spent_on=month_start,
            )
        )

        for name, notes, low, high, per_month in SPENDING_PATTERN:
            for _ in range(random.randint(max(1, per_month - 2), per_month + 1)):
                day = random.randint(1, 27)
                spent_on = month_start.replace(day=day)
                if spent_on > today:
                    continue
                db.session.add(
                    Transaction(
                        user_id=user.id,
                        type=EXPENSE,
                        category_id=categories[name].id,
                        amount=money(low, high),
                        note=random.choice(notes),
                        spent_on=spent_on,
                    )
                )

    db.session.add(
        RecurringExpense(
            user_id=user.id,
            category_id=categories["Rent"].id,
            title="Room rent",
            amount=Decimal("12000"),
            frequency=MONTHLY,
            start_on=today.replace(day=1),
            next_due_on=today.replace(day=1),
        )
    )
    db.session.add(
        RecurringExpense(
            user_id=user.id,
            category_id=categories["Entertainment"].id,
            title="Streaming subscription",
            amount=Decimal("499"),
            frequency=MONTHLY,
            start_on=today.replace(day=5),
            next_due_on=today.replace(day=5),
        )
    )
    db.session.add(
        RecurringExpense(
            user_id=user.id,
            category_id=categories["Transport"].id,
            title="Weekly bus pass",
            amount=Decimal("350"),
            frequency=WEEKLY,
            start_on=today - timedelta(days=21),
            next_due_on=today - timedelta(days=21),
        )
    )

    month_key = today.strftime("%Y-%m")
    for name, limit in [
        ("Food", 12000),
        ("Transport", 4000),
        ("Shopping", 5000),
        ("Entertainment", 3000),
        ("Bills & Utilities", 5000),
    ]:
        db.session.add(
            Budget(
                user_id=user.id,
                category_id=categories[name].id,
                month=month_key,
                amount_limit=Decimal(limit),
            )
        )

    laptop = SavingsGoal(
        user_id=user.id,
        title="New laptop",
        target_amount=Decimal("80000"),
        target_date=today + timedelta(days=180),
        note="For final year project work",
    )
    emergency = SavingsGoal(
        user_id=user.id,
        title="Emergency fund",
        target_amount=Decimal("25000"),
        note="Three months of essentials",
    )
    db.session.add_all([laptop, emergency])
    db.session.flush()

    for months_back in range(4):
        db.session.add(
            GoalContribution(
                goal_id=laptop.id,
                amount=Decimal("6000"),
                added_on=today - timedelta(days=30 * months_back),
                note="Monthly saving",
            )
        )
    db.session.add(
        GoalContribution(
            goal_id=emergency.id,
            amount=Decimal("25000"),
            added_on=today - timedelta(days=10),
            note="Transferred savings",
        )
    )
    emergency.refresh_status()

    db.session.commit()
    return user


def main():
    app = create_app()
    with app.app_context():
        db.create_all()
        clear_demo_account()
        user = build_demo_account()

        print("Demo data created.")
        print(f"  Email:    {DEMO_EMAIL}")
        print(f"  Password: {DEMO_PASSWORD}")
        print(f"  {user.transactions.count()} transactions, "
              f"{user.budgets.count()} budgets, {user.goals.count()} goals.")
        print("Sign in, then read the verification code from the console or logs/otp.log.")


if __name__ == "__main__":
    main()

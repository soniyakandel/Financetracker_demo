# Finance Tracker

A personal finance tracker built with Flask, Jinja2 and SQLAlchemy.

Author: **Soniya Kandel**

## Run

```bash
cd Financetracker_demo

python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt

flask --app run init-db             # create tables
python run.py                       # http://127.0.0.1:5000
```

Settings (secret key, database, session and login limits) are read from the
`.env` file included with the project.


Tests: `python -m pytest`

## Features

- **Expenses** — add, edit and delete expenses and income, with date-range,
  category, type and note filters, sorting, pagination and running totals.

- **Categories** — ten defaults per account, plus custom ones with a chosen
  icon and colour.

- **Recurring expenses** — weekly or monthly rules entered automatically when
  due; can be paused and resumed.

- **Budgets** — a monthly limit per category with a progress bar that warns at
  80% and turns red once passed.

- **Savings goals** — a target amount and date, contributions over time, and
  automatic completion when filled.

- **Dashboard** — money in, money out, balance and total saved against last
  month, a category doughnut chart, six-month trend, budget watchlist and
  recent activity.
  
- **Accounts and sessions** — registration with a password policy, a two-step
  verification code at every sign-in, account lockout and rate limits,
  server-side sessions with idle and absolute timeouts, an active devices page
  for revoking any session, and a security activity log.
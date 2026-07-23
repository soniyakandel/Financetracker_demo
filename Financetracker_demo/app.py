from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

CATEGORIES = ["Food", "Transport", "Shopping", "Bills", "Other"]

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"

db = SQLAlchemy(app)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    amount = db.Column(db.Float)
    date = db.Column(db.Date)
    category = db.Column(db.String(50))


@app.route("/")
def home():
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    return render_template("index.html", expenses=expenses)


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        expense = Expense(
            title=request.form["title"],
            amount=float(request.form["amount"]),
            date=datetime.strptime(request.form["date"], "%Y-%m-%d").date(),
            category=request.form["category"],
        )
        db.session.add(expense)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("add.html", categories=CATEGORIES)


@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
def edit(expense_id):
    expense = Expense.query.get(expense_id)
    if request.method == "POST":
        expense.title = request.form["title"]
        expense.amount = float(request.form["amount"])
        expense.date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        expense.category = request.form["category"]
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("edit.html", expense=expense, categories=CATEGORIES)


@app.route("/delete/<int:expense_id>")
def delete(expense_id):
    expense = Expense.query.get(expense_id)
    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for("home"))


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)

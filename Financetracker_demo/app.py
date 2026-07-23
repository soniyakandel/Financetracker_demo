from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"

db = SQLAlchemy(app)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    amount = db.Column(db.String(50))
    date = db.Column(db.String(50))


@app.route("/")
def home():
    expenses = Expense.query.all()
    return render_template("index.html", expenses=expenses)


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        expense = Expense(
            title=request.form["title"],
            amount=request.form["amount"],
            date=request.form["date"],
        )
        db.session.add(expense)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("add.html")


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, render_template
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
    return render_template("index.html")


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)

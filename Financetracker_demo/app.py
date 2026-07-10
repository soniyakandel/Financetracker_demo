from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>Welcome to Finance Tracker</h1>"

# Run the application
if __name__ == '__main__':
    app.run(debug=True)
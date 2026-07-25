import re

import pytest

from app import create_app
from app.extensions import db
from app.models.category import Category
from app.models.user import User

PASSWORD = "Str0ng!Pass"


@pytest.fixture
def app():
    application = create_app("testing")
    application.config["OTP_SHOW_IN_BROWSER"] = True
    with application.app_context():
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def make_user(app):
    def _make(email="user@example.com", name="Test User", password=PASSWORD):
        with app.app_context():
            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            Category.create_defaults_for(user)
            db.session.commit()
            return user.id

    return _make


@pytest.fixture
def user_id(make_user):
    return make_user()


def sign_in(app, email="user@example.com", password=PASSWORD):
    client = app.test_client()
    body = client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    ).get_data(as_text=True)

    match = re.search(r"code is (\d{6})", body)
    assert match, "the development verification code was not shown"
    client.post("/auth/verify", data={"code": match.group(1)})
    return client


@pytest.fixture
def client(app, user_id):
    return sign_in(app)

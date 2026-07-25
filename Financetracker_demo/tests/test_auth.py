from app.extensions import db
from app.models.category import Category
from app.models.user import User
from tests.conftest import PASSWORD, sign_in


def test_registration_creates_user_with_default_categories(app):
    client = app.test_client()
    response = client.post(
        "/auth/register",
        data={
            "name": "Soniya Kandel",
            "email": "soniya@example.com",
            "password": "F1nance!2026",
            "confirm_password": "F1nance!2026",
            "accept_terms": "y",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="soniya@example.com").first()
        assert user is not None
        assert user.password_hash != "F1nance!2026"
        assert user.check_password("F1nance!2026")
        assert Category.query.filter_by(user_id=user.id).count() == 10


def test_registration_rejects_a_weak_password(app):
    client = app.test_client()
    response = client.post(
        "/auth/register",
        data={
            "name": "Weak User",
            "email": "weak@example.com",
            "password": "password",
            "confirm_password": "password",
            "accept_terms": "y",
        },
    )

    assert b"Password must contain" in response.data
    with app.app_context():
        assert User.query.filter_by(email="weak@example.com").first() is None


def test_duplicate_email_is_refused_without_confirming_it_exists(app, user_id):
    client = app.test_client()
    response = client.post(
        "/auth/register",
        data={
            "name": "Copy Cat",
            "email": "user@example.com",
            "password": "F1nance!2026",
            "confirm_password": "F1nance!2026",
            "accept_terms": "y",
        },
    )

    body = response.get_data(as_text=True)
    assert "could not create that account" in body
    assert "user@example.com is already" not in body
    with app.app_context():
        assert User.query.filter_by(email="user@example.com").count() == 1


def test_wrong_password_gives_the_same_message_as_unknown_email(app, user_id):
    client = app.test_client()
    known = client.post(
        "/auth/login", data={"email": "user@example.com", "password": "wrong"}
    ).get_data(as_text=True)
    unknown = client.post(
        "/auth/login", data={"email": "nobody@example.com", "password": "wrong"}
    ).get_data(as_text=True)

    assert "Email or password is incorrect." in known
    assert "Email or password is incorrect." in unknown


def test_account_locks_after_repeated_failures(app, user_id):
    client = app.test_client()
    for _ in range(app.config["MAX_LOGIN_ATTEMPTS"]):
        client.post("/auth/login", data={"email": "user@example.com", "password": "wrong"})

    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.failed_attempts == app.config["MAX_LOGIN_ATTEMPTS"]
        assert user.is_currently_locked

    response = client.post(
        "/auth/login", data={"email": "user@example.com", "password": PASSWORD}
    )
    assert b"temporarily locked" in response.data


def test_password_alone_does_not_sign_a_user_in(app, user_id):
    client = app.test_client()
    client.post(
        "/auth/login", data={"email": "user@example.com", "password": PASSWORD}
    )

    assert client.get("/dashboard/").status_code == 302


def test_wrong_verification_code_is_refused(app, user_id):
    client = app.test_client()
    client.post("/auth/login", data={"email": "user@example.com", "password": PASSWORD})

    response = client.post("/auth/verify", data={"code": "000000"})
    assert b"not correct" in response.data
    assert client.get("/dashboard/").status_code == 302


def test_verification_code_cannot_be_reused(app, user_id):
    import re

    client = app.test_client()
    body = client.post(
        "/auth/login",
        data={"email": "user@example.com", "password": PASSWORD},
        follow_redirects=True,
    ).get_data(as_text=True)
    code = re.search(r"code is (\d{6})", body).group(1)

    client.post("/auth/verify", data={"code": code})
    assert client.get("/dashboard/").status_code == 200

    other = app.test_client()
    other.post("/auth/login", data={"email": "user@example.com", "password": PASSWORD})
    other.post("/auth/verify", data={"code": code})
    assert other.get("/dashboard/").status_code == 302


def test_signed_in_user_reaches_the_dashboard(app, user_id):
    client = sign_in(app)
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"Dashboard" in response.data

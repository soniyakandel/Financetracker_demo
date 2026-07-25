from datetime import date

from app.extensions import db
from app.models.category import Category
from app.models.transaction import Transaction
from app.security.passwords import hash_password, verify_password
from app.security.policy import check_password_strength
from tests.conftest import sign_in


def test_passwords_are_salted_and_never_stored_in_the_clear():
    first = hash_password("Str0ng!Pass")
    second = hash_password("Str0ng!Pass")

    assert "Str0ng!Pass" not in first
    assert first != second
    assert verify_password(first, "Str0ng!Pass")
    assert not verify_password(first, "Str0ng!Pas")


def test_the_password_policy_rejects_weak_choices():
    assert check_password_strength("Str0ng!Pass") == []
    assert check_password_strength("short") != []
    assert check_password_strength("alllowercase1!") != []
    assert check_password_strength("NOLOWERCASE1!") != []
    assert check_password_strength("NoDigits!!") != []
    assert check_password_strength("NoSymbol123") != []
    assert check_password_strength("password123") != []


def test_security_headers_are_present_on_every_response(app):
    response = app.test_client().get("/")

    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "same-origin"
    policy = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in policy
    assert "frame-ancestors 'none'" in policy
    assert "object-src 'none'" in policy


def test_the_session_cookie_is_locked_down(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_a_script_in_a_note_is_shown_as_text_not_run(app, user_id):
    client = sign_in(app)
    with app.app_context():
        category_id = Category.query.filter_by(user_id=user_id).first().id

    client.post(
        "/expenses/new",
        data={
            "type": "expense",
            "amount": "100",
            "category_id": category_id,
            "spent_on": date.today().isoformat(),
            "note": "<script>alert('xss')</script>",
        },
    )

    body = client.get("/expenses/").get_data(as_text=True)
    assert "<script>alert('xss')</script>" not in body
    assert "&lt;script&gt;" in body


def test_filters_do_not_pass_raw_values_into_sql(app, user_id):
    client = sign_in(app)
    with app.app_context():
        category_id = Category.query.filter_by(user_id=user_id).first().id
        db.session.add(
            Transaction(user_id=user_id, type="expense", amount=100,
                        category_id=category_id, spent_on=date.today())
        )
        db.session.commit()

    response = client.get(
        "/expenses/?type=BOGUS&category=abc&sort=;DROP TABLE users;--&search=' OR '1'='1"
    )
    assert response.status_code == 200

    with app.app_context():
        assert Transaction.query.count() == 1


def test_state_changing_routes_reject_a_get(app, user_id):
    client = sign_in(app)
    assert client.get("/expenses/1/delete").status_code == 405
    assert client.get("/auth/logout").status_code == 405
    assert client.get("/profile/sessions/revoke-others").status_code == 405


def test_csrf_protection_blocks_a_tokenless_post():
    from app import create_app

    application = create_app("development")
    application.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    assert application.config["WTF_CSRF_ENABLED"] is True

    with application.app_context():
        db.create_all()

    response = application.test_client().post(
        "/auth/login", data={"email": "a@example.com", "password": "whatever"}
    )
    assert response.status_code == 302


def test_open_redirects_are_not_followed(app):
    with app.test_request_context("/"):
        from app.security.urls import is_safe_url

        assert is_safe_url("/dashboard/")
        assert not is_safe_url("http://evil.example.com/steal")
        assert not is_safe_url("//evil.example.com")

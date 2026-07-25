from datetime import timedelta

from app.extensions import db
from app.models.base import utcnow
from app.models.session import UserSession
from tests.conftest import sign_in


def test_signing_in_creates_a_session_record(app, user_id):
    sign_in(app)
    with app.app_context():
        record = UserSession.query.filter_by(user_id=user_id).one()
        assert record.is_active
        assert record.is_valid
        assert len(record.session_token) == 64


def test_each_sign_in_gets_a_fresh_token(app, user_id):
    sign_in(app)
    sign_in(app)
    with app.app_context():
        tokens = [r.session_token for r in UserSession.query.all()]
        assert len(tokens) == 2
        assert tokens[0] != tokens[1]


def test_idle_timeout_signs_the_user_out(app, user_id):
    client = sign_in(app)
    assert client.get("/dashboard/").status_code == 200

    with app.app_context():
        record = UserSession.query.filter_by(user_id=user_id).one()
        idle = app.config["SESSION_IDLE_MINUTES"]
        record.last_seen_at = utcnow() - timedelta(minutes=idle + 1)
        db.session.commit()

    response = client.get("/dashboard/", follow_redirects=True)
    assert b"minutes of inactivity" in response.data
    with app.app_context():
        assert UserSession.query.filter_by(user_id=user_id).one().revoked_reason == "idle_timeout"


def test_absolute_lifetime_signs_the_user_out(app, user_id):
    client = sign_in(app)

    with app.app_context():
        record = UserSession.query.filter_by(user_id=user_id).one()
        record.expires_at = utcnow() - timedelta(minutes=1)
        db.session.commit()

    response = client.get("/dashboard/", follow_redirects=True)
    assert b"sessions expire after" in response.data


def test_activity_pushes_the_idle_window_forward(app, user_id):
    client = sign_in(app)
    with app.app_context():
        record = UserSession.query.filter_by(user_id=user_id).one()
        record.last_seen_at = utcnow() - timedelta(minutes=5)
        db.session.commit()
        stale = record.last_seen_at

    client.get("/dashboard/")
    with app.app_context():
        assert UserSession.query.filter_by(user_id=user_id).one().last_seen_at > stale


def test_revoking_a_device_ends_it_on_its_next_request(app, user_id):
    first = sign_in(app)
    second = sign_in(app)

    with app.app_context():
        ids = [r.id for r in UserSession.query.order_by(UserSession.id).all()]

    first.post(f"/profile/sessions/{ids[1]}/revoke")

    response = second.get("/dashboard/", follow_redirects=True)
    assert b"signed out from your account" in response.data
    assert first.get("/dashboard/").status_code == 200


def test_revoke_all_others_keeps_the_current_device(app, user_id):
    first = sign_in(app)
    second = sign_in(app)
    third = sign_in(app)

    first.post("/profile/sessions/revoke-others")

    assert first.get("/dashboard/").status_code == 200
    assert second.get("/dashboard/").status_code == 302
    assert third.get("/dashboard/").status_code == 302


def test_logout_revokes_the_session_record(app, user_id):
    client = sign_in(app)
    client.post("/auth/logout")

    with app.app_context():
        record = UserSession.query.filter_by(user_id=user_id).one()
        assert not record.is_active
        assert record.revoked_reason == "logout"


def test_changing_the_password_ends_other_devices(app, user_id):
    first = sign_in(app)
    second = sign_in(app)

    first.post(
        "/profile/password",
        data={
            "current_password": "Str0ng!Pass",
            "new_password": "F1nance!2026",
            "confirm_password": "F1nance!2026",
        },
    )

    assert first.get("/dashboard/").status_code == 200
    assert second.get("/dashboard/").status_code == 302

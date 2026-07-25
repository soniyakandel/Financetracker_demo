from app.extensions import db
from app.models.revoked_token import RevokedToken
from tests.conftest import PASSWORD


def api_login(client, email="user@example.com", password=PASSWORD):
    return client.post("/api/login", json={"email": email, "password": password})


def auth_header(token):
    return {"Authorization": "Bearer " + token}


def test_login_returns_a_token_pair(app, user_id):
    response = api_login(app.test_client())

    assert response.status_code == 200
    assert response.json["token_type"] == "Bearer"
    assert response.json["access_token"]
    assert response.json["refresh_token"]


def test_login_rejects_a_wrong_password(app, user_id):
    response = api_login(app.test_client(), password="not-the-password")

    assert response.status_code == 401
    assert response.json["error"] == "invalid_credentials"
    assert "access_token" not in response.json


def test_login_does_not_say_whether_the_email_exists(app, user_id):
    unknown = api_login(app.test_client(), email="nobody@example.com")
    wrong = api_login(app.test_client(), password="not-the-password")

    assert unknown.status_code == wrong.status_code
    assert unknown.json == wrong.json


def test_protected_endpoint_needs_a_token(app, user_id):
    response = app.test_client().get("/api/me")

    assert response.status_code == 401
    assert response.json["error"] == "missing_token"


def test_protected_endpoint_rejects_a_tampered_token(app, user_id):
    client = app.test_client()
    token = api_login(client).json["access_token"]
    tampered = token[:-2] + ("aa" if not token.endswith("aa") else "bb")

    response = client.get("/api/me", headers=auth_header(tampered))

    assert response.status_code == 401
    assert response.json["error"] == "invalid_token"


def test_token_gives_access_to_the_owner_only(app, user_id, make_user):
    other_id = make_user(email="other@example.com", name="Other")
    client = app.test_client()
    token = api_login(client).json["access_token"]

    response = client.get("/api/me", headers=auth_header(token))

    assert response.status_code == 200
    assert response.json["id"] == user_id
    assert response.json["id"] != other_id


def test_refresh_gives_a_new_pair_and_burns_the_old_one(app, user_id):
    client = app.test_client()
    tokens = api_login(client).json

    first = client.post("/api/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200
    assert first.json["access_token"] != tokens["access_token"]

    replay = client.post("/api/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401
    assert replay.json["error"] == "invalid_token"


def test_logout_revokes_the_access_token(app, user_id):
    client = app.test_client()
    tokens = api_login(client).json
    header = auth_header(tokens["access_token"])

    assert client.get("/api/me", headers=header).status_code == 200

    signed_out = client.post(
        "/api/logout", headers=header, json={"refresh_token": tokens["refresh_token"]}
    )
    assert signed_out.status_code == 200

    assert client.get("/api/me", headers=header).status_code == 401
    with app.app_context():
        assert RevokedToken.query.count() == 2


def test_locked_account_cannot_get_a_token(app, user_id):
    client = app.test_client()
    for _ in range(app.config["MAX_LOGIN_ATTEMPTS"]):
        api_login(client, password="not-the-password")

    response = api_login(client)

    assert response.status_code == 423
    assert response.json["error"] == "account_locked"

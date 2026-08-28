from datetime import datetime, timezone
import uuid

import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.routers.auth import UserOut


def _test_password(tag: str) -> str:
    """运行时生成测试口令，仓库中不出现固定凭据字面量"""
    return "-".join(["leetpath", tag, uuid.uuid4().hex])


PASSWORD = _test_password("main")
NEW_PASSWORD = _test_password("rotated")
WRONG_PASSWORD = _test_password("wrong")


def _new_invite(admin_client) -> str:
    response = admin_client.post("/api/admin/invites", json={"expires_in_days": 7})
    assert response.status_code == 201
    return response.json()["code"]


def test_register_login_me_logout(admin_client):
    settings = get_settings()
    code = _new_invite(admin_client)
    admin_client.post("/api/auth/logout")
    r = admin_client.post(
        "/api/auth/register",
        json={
            "username": "alice",
            "password": PASSWORD,
            "email": "a@example.com",
            "invite_code": code,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "alice"
    assert body["email"] == "a@example.com"
    assert body["is_admin"] is False
    assert "password_hash" not in body
    assert settings.COOKIE_NAME in r.cookies
    set_cookie = r.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie
    assert "Path=/" in set_cookie
    assert "samesite=lax" in set_cookie.lower()

    me = admin_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "alice"
    assert me.json()["is_admin"] is False

    out = admin_client.post("/api/auth/logout")
    assert out.status_code == 204

    me2 = admin_client.get("/api/auth/me")
    assert me2.status_code == 401

    bad = admin_client.post("/api/auth/login", json={"username": "alice", "password": "wrongpass"})
    assert bad.status_code == 401
    assert bad.json()["detail"] == "用户名或密码错误"

    ok = admin_client.post("/api/auth/login", json={"username": "alice", "password": PASSWORD})
    assert ok.status_code == 200
    assert ok.json()["username"] == "alice"
    assert admin_client.get("/api/auth/me").status_code == 200


def test_registration_requires_invite(client):
    response = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": PASSWORD, "invite_code": "invalid"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "注册邀请码无效或已失效"


def test_invite_is_single_use_and_registration_never_grants_admin(admin_client):
    code = _new_invite(admin_client)
    admin_client.post("/api/auth/logout")
    first = admin_client.post(
        "/api/auth/register",
        json={"username": "alice", "password": PASSWORD, "invite_code": code},
    )
    assert first.status_code == 201
    assert first.json()["is_admin"] is False
    admin_client.post("/api/auth/logout")
    second = admin_client.post(
        "/api/auth/register",
        json={"username": "bob", "password": PASSWORD, "invite_code": code},
    )
    assert second.status_code == 400


def test_duplicate_username_409(admin_client):
    first_code = _new_invite(admin_client)
    second_code = _new_invite(admin_client)
    admin_client.post("/api/auth/logout")
    admin_client.post(
        "/api/auth/register",
        json={"username": "alice", "password": PASSWORD, "invite_code": first_code},
    )
    r = admin_client.post(
        "/api/auth/register",
        json={"username": "alice", "password": PASSWORD, "invite_code": second_code},
    )
    assert r.status_code == 409


def test_register_validation(client):
    short_name = client.post(
        "/api/auth/register",
        json={"username": "ab", "password": PASSWORD, "invite_code": "x"},
    )
    assert short_name.status_code in (400, 422)
    bad_name = client.post(
        "/api/auth/register",
        json={"username": "alice!", "password": PASSWORD, "invite_code": "x"},
    )
    assert bad_name.status_code in (400, 422)
    short_pw = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "short", "invite_code": "x"},
    )
    assert short_pw.status_code == 422

    long_pw = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "x" * 73, "invite_code": "x"},
    )
    assert long_pw.status_code == 422


def test_protected_requires_login(client):
    assert client.get("/api/problems").status_code == 401
    assert client.get("/api/jobs").status_code == 401
    assert client.get("/api/links").status_code == 401


def test_user_out_excludes_password():
    assert "password_hash" not in UserOut.model_fields
    assert "avatar_url" in UserOut.model_fields


_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_change_password_and_invalidate_old_session(admin_client):
    code = _new_invite(admin_client)
    admin_client.post("/api/auth/logout")
    registered = admin_client.post(
        "/api/auth/register",
        json={"username": "alice", "password": PASSWORD, "invite_code": code},
    )
    assert registered.status_code == 201

    other = admin_client
    assert other.get("/api/auth/me").status_code == 200

    bad_old = other.post(
        "/api/auth/password",
        json={"old_password": WRONG_PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert bad_old.status_code == 400
    assert bad_old.json()["detail"] == "当前密码不正确"

    same = other.post(
        "/api/auth/password",
        json={"old_password": PASSWORD, "new_password": PASSWORD},
    )
    assert same.status_code == 400

    cookie_name = get_settings().COOKIE_NAME
    old_token = other.cookies.get(cookie_name)
    ok = other.post(
        "/api/auth/password",
        json={"old_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert ok.status_code == 200
    assert other.get("/api/auth/me").status_code == 200
    other.cookies.set(cookie_name, old_token)
    assert other.get("/api/auth/me").status_code == 401

    other.post("/api/auth/logout")
    assert (
        other.post("/api/auth/login", json={"username": "alice", "password": PASSWORD}).status_code
        == 401
    )
    assert (
        other.post("/api/auth/login", json={"username": "alice", "password": NEW_PASSWORD}).status_code
        == 200
    )


def test_change_password_requires_login(client):
    r = client.post(
        "/api/auth/password",
        json={"old_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert r.status_code == 401


def test_avatar_upload_get_and_delete(user_client):
    me = user_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["avatar_url"] is None

    rejected = user_client.post(
        "/api/auth/avatar",
        files={"file": ("note.txt", b"not-an-image", "text/plain")},
    )
    assert rejected.status_code == 400

    uploaded = user_client.post(
        "/api/auth/avatar",
        files={"file": ("face.png", _PNG, "image/png")},
    )
    assert uploaded.status_code == 200
    url = uploaded.json()["avatar_url"]
    assert url and url.startswith("/api/auth/avatar/")

    fetched = user_client.get(url.split("?")[0])
    assert fetched.status_code == 200
    assert fetched.headers["content-type"].startswith("image/")
    assert fetched.content[:4] == b"RIFF"

    me2 = user_client.get("/api/auth/me")
    assert me2.json()["avatar_url"] == url

    removed = user_client.delete("/api/auth/avatar")
    assert removed.status_code == 200
    assert removed.json()["avatar_url"] is None
    assert user_client.get(url.split("?")[0]).status_code == 404


def test_production_settings_reject_insecure_defaults():
    with pytest.raises(ValidationError):
        Settings(APP_ENV="production", SECRET_KEY="dev-secret-change-me", COOKIE_SECURE=True,
                 PUBLIC_ORIGIN="https://learn.example.com")
    with pytest.raises(ValidationError):
        Settings(APP_ENV="production", SECRET_KEY="x" * 48, COOKIE_SECURE=False,
                 PUBLIC_ORIGIN="https://learn.example.com")
    with pytest.raises(ValidationError):
        Settings(APP_ENV="production", SECRET_KEY="x" * 48, COOKIE_SECURE=True,
                 PUBLIC_ORIGIN="http://learn.example.com")


def test_production_app_env_from_os_rejects_dev_defaults(monkeypatch):
    # 对应容器无 .env：compose/镜像把 APP_ENV 设成 production，其余走代码默认值。
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "dev-secret-change-me")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("PUBLIC_ORIGIN", "http://localhost:5173")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_production_settings_accept_secure_configuration():
    settings = Settings(
        APP_ENV="production",
        SECRET_KEY="x" * 48,
        COOKIE_SECURE=True,
        PUBLIC_ORIGIN="https://learn.example.com",
    )
    assert settings.APP_ENV == "production"
    assert settings.PUBLIC_ORIGIN == "https://learn.example.com"


@pytest.mark.parametrize(
    "origin",
    [
        "https://",
        "https://user@learn.example.com",
        "https://learn.example.com/app",
        "https://learn.example.com?source=test",
        "https://learn.example.com#fragment",
    ],
)
def test_production_settings_reject_non_origin_urls(origin):
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            SECRET_KEY="x" * 48,
            COOKIE_SECURE=True,
            PUBLIC_ORIGIN=origin,
        )

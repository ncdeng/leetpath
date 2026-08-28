import uuid


def _test_password(tag: str) -> str:
    """运行时生成测试口令，仓库中不出现固定凭据字面量"""
    return "-".join(["leetpath", tag, uuid.uuid4().hex])


PASSWORD = _test_password("main")


def test_production_rejects_missing_or_untrusted_origin(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "x" * 48)
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://learn.example.com")

    missing = client.post("/api/auth/login", json={"username": "none", "password": PASSWORD})
    assert missing.status_code == 403
    untrusted = client.post(
        "/api/auth/login",
        json={"username": "none", "password": PASSWORD},
        headers={"Origin": "https://evil.example"},
    )
    assert untrusted.status_code == 403
    trusted = client.post(
        "/api/auth/login",
        json={"username": "none", "password": PASSWORD},
        headers={"Origin": "https://learn.example.com"},
    )
    assert trusted.status_code == 401


def test_login_is_rate_limited(client):
    statuses = [
        client.post(
            "/api/auth/login",
            json={"username": "missing", "password": PASSWORD},
        ).status_code
        for _ in range(6)
    ]
    assert statuses[:5] == [401] * 5
    assert statuses[5] == 429
    assert client.post(
        "/api/auth/login",
        json={"username": "other", "password": PASSWORD},
    ).status_code == 401


def test_login_ip_is_rate_limited(client):
    statuses = [
        client.post(
            "/api/auth/login",
            json={"username": f"user{i}", "password": PASSWORD},
        ).status_code
        for i in range(21)
    ]
    assert statuses[:20] == [401] * 20
    assert statuses[20] == 429

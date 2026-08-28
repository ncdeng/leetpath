def test_ai_rejects_host_not_in_allowlist(admin_client):
    """白名单外的目标（含内网地址）应被拒绝，防止 SSRF"""
    r = admin_client.post(
        "/api/ai/models",
        json={"base_url": "http://backend:8000/v1", "api_key": "sk-test"},
    )
    assert r.status_code == 400
    assert "允许列表" in r.json()["detail"]

    r2 = admin_client.post(
        "/api/ai/chat",
        json={
            "base_url": "http://169.254.169.254/v1",
            "api_key": "sk-test",
            "model": "m",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert r2.status_code == 400


def test_ai_rejects_non_http_scheme(admin_client):
    r = admin_client.post(
        "/api/ai/models",
        json={"base_url": "file:///etc/passwd", "api_key": "sk-test"},
    )
    assert r.status_code == 400


def test_chat_upstream_body_forwards_reasoning_effort():
    from app.routers.ai import ChatStreamRequest, chat_upstream_body

    payload = ChatStreamRequest(
        model="grok-4.6",
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.4,
        max_tokens=2048,
        reasoning_effort="high",
    )
    body = chat_upstream_body(payload, "grok-4.6")
    assert body["reasoning_effort"] == "high"
    assert body["temperature"] == 0.4
    assert body["max_tokens"] == 2048
    assert body["max_completion_tokens"] == 2048
    assert body["stream"] is True
    assert body["max_tokens"] + 128 <= 256000

    off = ChatStreamRequest(
        model="grok-4.6",
        messages=[{"role": "user", "content": "hi"}],
        reasoning_effort="off",
    )
    off_body = chat_upstream_body(off, "grok-4.6")
    assert "reasoning_effort" not in off_body
    assert off_body["max_completion_tokens"] == 4096

    huge = ChatStreamRequest(
        model="grok-4.6",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=256000,
    )
    huge_body = chat_upstream_body(huge, "grok-4.6")
    assert huge_body["max_tokens"] == huge_body["max_completion_tokens"]
    assert huge_body["max_completion_tokens"] < 256000
    assert huge_body["max_completion_tokens"] <= 256000 - 64


def test_chat_rejects_unknown_reasoning_effort(admin_client):
    r = admin_client.post(
        "/api/ai/chat",
        json={
            "base_url": "https://api.antithor.asia/v1",
            "api_key": "sk-test",
            "model": "grok-4.6",
            "messages": [{"role": "user", "content": "hi"}],
            "reasoning_effort": "ultra",
        },
    )
    assert r.status_code == 422


def test_ai_requires_login(client):
    r = client.post(
        "/api/ai/models",
        json={"base_url": "https://api.deepseek.com/v1", "api_key": "sk-test"},
    )
    assert r.status_code == 401


def test_resolve_upstream_credentials_rules():
    from fastapi import HTTPException
    import pytest

    from app.routers.ai import _resolve_upstream_credentials

    # 两空：key 与地址同源回落系统配置
    assert _resolve_upstream_credentials("", "", "sk-sys", "https://sys/v1") == (
        "sk-sys",
        "https://sys/v1",
    )
    # 只填 key：地址回落系统默认
    assert _resolve_upstream_credentials("sk-user", "", "sk-sys", "https://sys/v1") == (
        "sk-user",
        "https://sys/v1",
    )
    # key + 自定义地址：完全用用户的
    assert _resolve_upstream_credentials(
        "sk-user", "https://api.deepseek.com/v1", "sk-sys", "https://sys/v1"
    ) == ("sk-user", "https://api.deepseek.com/v1")
    # 地址等于系统默认：允许回落系统 key
    assert _resolve_upstream_credentials("", "https://sys/v1/", "sk-sys", "https://sys/v1") == (
        "sk-sys",
        "https://sys/v1/",
    )
    # 自定义地址但没 key：拒绝，绝不把系统 Key 发往别家
    with pytest.raises(HTTPException) as exc_info:
        _resolve_upstream_credentials("", "https://api.deepseek.com/v1", "sk-sys", "https://sys/v1")
    assert exc_info.value.status_code == 400


def test_chat_rejects_custom_base_url_without_key(admin_client, monkeypatch):
    """系统 Key 存在时，用户换 base_url 且不带 key 也不得借用系统 Key（凭据外泄）"""
    monkeypatch.setenv("SYSTEM_AI_API_KEY", "sk-system-shared-secret")
    r = admin_client.post(
        "/api/ai/chat",
        json={
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "",
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert r.status_code == 400
    assert "API Key" in r.json()["detail"]


def test_models_rejects_custom_base_url_without_key(admin_client, monkeypatch):
    monkeypatch.setenv("SYSTEM_AI_API_KEY", "sk-system-shared-secret")
    r = admin_client.post(
        "/api/ai/models",
        json={"base_url": "https://api.deepseek.com/v1", "api_key": ""},
    )
    assert r.status_code == 400


def test_system_key_still_works_with_default_base_url(admin_client, monkeypatch):
    """默认地址 + 空 key 应照常走系统 Key：凭据检查放行，转发失败只体现为 SSE 错误事件"""
    monkeypatch.setenv("SYSTEM_AI_API_KEY", "sk-system-shared-secret")
    # 指向本机保留端口，连接立即被拒，测试不出外网
    monkeypatch.setenv("SYSTEM_AI_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("AI_ALLOWED_HOSTS", "api.antithor.asia,api.deepseek.com,127.0.0.1")
    r = admin_client.post(
        "/api/ai/chat",
        json={
            "base_url": "",
            "api_key": "",
            "model": "grok-4.6",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert r.status_code == 200
    assert "error" in r.text


def test_chat_response_sets_no_buffering_header(admin_client, monkeypatch):
    """SSE 响应必须带 X-Accel-Buffering: no，否则 nginx 攒批破坏流式"""
    monkeypatch.setenv("SYSTEM_AI_API_KEY", "sk-system-shared-secret")
    monkeypatch.setenv("SYSTEM_AI_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("AI_ALLOWED_HOSTS", "api.antithor.asia,api.deepseek.com,127.0.0.1")
    r = admin_client.post(
        "/api/ai/chat",
        json={
            "base_url": "",
            "api_key": "",
            "model": "grok-4.6",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert r.headers.get("x-accel-buffering") == "no"

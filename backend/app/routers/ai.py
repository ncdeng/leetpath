from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
import httpx
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models import User

router = APIRouter(prefix="/ai", tags=["ai"])


def _validate_base_url(base_url: str) -> None:
    """仅允许转发到服务端白名单内的 AI 服务，防止借代理探测内网（SSRF）"""
    parsed = urlparse(base_url.strip())
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="base_url 必须是 http(s) 地址",
        )
    host = (parsed.hostname or "").lower()
    allowed = {
        h.strip().lower()
        for h in get_settings().AI_ALLOWED_HOSTS.split(",")
        if h.strip()
    }
    if host not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AI 服务地址 {host or '(空)'} 不在服务端允许列表，如需使用请在 .env 的 AI_ALLOWED_HOSTS 中追加",
        )


def _get_effective_ai_config(db: Session) -> tuple[str, str, str]:
    from app.models import SystemSetting
    settings = get_settings()

    k_rec = db.get(SystemSetting, "ai_api_key")
    u_rec = db.get(SystemSetting, "ai_base_url")
    m_rec = db.get(SystemSetting, "ai_model")

    key = (k_rec.value if k_rec and k_rec.value.strip() else "") or settings.SYSTEM_AI_API_KEY.strip()
    url = (u_rec.value if u_rec and u_rec.value.strip() else "") or settings.SYSTEM_AI_BASE_URL.strip()
    model = (m_rec.value if m_rec and m_rec.value.strip() else "") or settings.SYSTEM_AI_MODEL.strip()
    return key, url, model


def _resolve_upstream_credentials(
    payload_key: str, payload_url: str, sys_key: str, sys_url: str
) -> tuple[str, str]:
    """决定转发用的 key 与 base_url，两者必须同源。

    系统内置 Key 只服务于系统默认地址：用户把 base_url 指向别家服务时必须
    自带 Key，否则等于把系统共享 Key 以 Bearer 头发给未授权的第三方。
    """
    key = payload_key.strip()
    url = payload_url.strip() or sys_url
    if payload_url.strip() and url.rstrip("/") != sys_url.rstrip("/") and not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="使用自定义服务地址时必须同时填写该服务的 API Key，系统内置 Key 仅限默认服务地址使用",
        )
    return key or sys_key, url


@router.get("/status")
def get_ai_status(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> dict[str, Any]:
    """返回服务端是否内置了内测 AI 密钥及默认模型信息"""
    sys_key, sys_url, sys_model = _get_effective_ai_config(db)
    return {
        "has_system_key": bool(sys_key),
        "default_base_url": sys_url,
        "default_model": sys_model,
    }


class FetchModelsRequest(BaseModel):
    base_url: str = ""
    api_key: str = ""


REASONING_EFFORTS = ("low", "medium", "high", "xhigh")
DEFAULT_MAX_OUTPUT_TOKENS = 4096
# Grok 4.6 等常见窗口；输出必须留出输入余量，否则 128 + 256000 会 400
MODEL_CONTEXT_LIMIT = 256000


def _estimate_message_tokens(messages: list[dict[str, Any]]) -> int:
    text_parts: list[str] = []
    for message in messages:
        content = message.get("content")
        if isinstance(content, str):
            text_parts.append(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    text_parts.append(part["text"])
    text = "".join(text_parts)
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return max(1, int(cjk * 1.5 + (len(text) - cjk) * 0.45) + 32)


def _capped_output_tokens(requested: int | None, input_tokens: int) -> int:
    want = requested if requested and requested > 0 else DEFAULT_MAX_OUTPUT_TOKENS
    room = max(16, MODEL_CONTEXT_LIMIT - input_tokens - 64)
    return min(int(want), room)


class ChatStreamRequest(BaseModel):
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    messages: list[dict[str, Any]]
    temperature: float = 0.7
    max_tokens: int | None = None
    reasoning_effort: str | None = None

    @field_validator("reasoning_effort")
    @classmethod
    def normalize_reasoning_effort(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if cleaned in ("", "off", "none", "false", "0"):
            return None
        if cleaned not in REASONING_EFFORTS:
            raise ValueError("reasoning_effort 须为 low / medium / high / xhigh，或不传")
        return cleaned


def chat_upstream_body(payload: ChatStreamRequest, model: str) -> dict[str, Any]:
    """组装转发给中转站的 chat/completions JSON。

    推理模型（Grok / o 系列）认 max_completion_tokens；若不传，中转站会默认成
    整段上下文窗口（如 256000），再加输入就会超过上限。
    """
    input_tokens = _estimate_message_tokens(payload.messages)
    output_tokens = _capped_output_tokens(payload.max_tokens, input_tokens)
    body: dict[str, Any] = {
        "model": model,
        "messages": payload.messages,
        "temperature": payload.temperature,
        "stream": True,
        "max_tokens": output_tokens,
        "max_completion_tokens": output_tokens,
    }
    if payload.reasoning_effort:
        body["reasoning_effort"] = payload.reasoning_effort
    return body


def _build_url(base_url: str, endpoint: str) -> str:
    cleaned = base_url.strip().rstrip("/")
    if cleaned.endswith("/v1"):
        return f"{cleaned}/{endpoint.lstrip('/')}"
    if "/v1/" in cleaned:
        return f"{cleaned}/{endpoint.lstrip('/')}"
    return f"{cleaned}/v1/{endpoint.lstrip('/')}"


@router.post("/models")
async def fetch_models(payload: FetchModelsRequest, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    sys_key, sys_url, _ = _get_effective_ai_config(db)
    clean_key, base_url = _resolve_upstream_credentials(payload.api_key, payload.base_url, sys_key, sys_url)
    if not clean_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先在 AI 设置中输入 API Key",
        )

    _validate_base_url(base_url)
    target_url = _build_url(base_url, "models")

    headers = {
        "Authorization": f"Bearer {clean_key}",
        "x-api-key": clean_key,
        "api-key": clean_key,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            resp = await client.get(target_url, headers=headers)
            
            # 如果 404，尝试不带 /v1 的直接路径
            if resp.status_code == 404 and "/v1/" in target_url:
                alt_url = target_url.replace("/v1/models", "/models")
                resp = await client.get(alt_url, headers=headers)

            if resp.status_code != 200:
                err_text = resp.text
                try:
                    err_json = resp.json()
                    err_text = err_json.get("message") or err_json.get("error") or str(err_json)
                except Exception:
                    pass
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"中转站验证未通过 ({resp.status_code}): {err_text[:200]}",
                )

            return resp.json()
    except HTTPException:
        raise
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"连接中转站接口失败: {str(exc)}",
        )


@router.post("/chat")
async def chat_stream(payload: ChatStreamRequest, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    sys_key, sys_url, sys_model = _get_effective_ai_config(db)
    clean_key, base_url = _resolve_upstream_credentials(payload.api_key, payload.base_url, sys_key, sys_url)
    if not clean_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未配置 API Key，请在 AI 设置中填入或由管理员在后台配置系统内置 Key",
        )

    model = payload.model.strip() or sys_model or "grok-4.6-xhigh"
    _validate_base_url(base_url)
    target_url = _build_url(base_url, "chat/completions")

    headers = {
        "Authorization": f"Bearer {clean_key}",
        "x-api-key": clean_key,
        "api-key": clean_key,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    body = chat_upstream_body(payload, model)
    timeout = 60.0
    if payload.reasoning_effort in ("medium", "high"):
        timeout = 180.0
    elif payload.reasoning_effort == "xhigh":
        timeout = 300.0

    async def event_generator():
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                async with client.stream("POST", target_url, headers=headers, json=body) as resp:
                    if resp.status_code != 200:
                        err_bytes = await resp.aread()
                        err_msg = err_bytes.decode("utf-8", errors="ignore")
                        try:
                            parsed = json.loads(err_msg)
                            err_msg = parsed.get("message") or parsed.get("error") or err_msg
                        except Exception:
                            pass
                        yield f"data: {json.dumps({'error': str(err_msg)[:300]})}\n\n"
                        return

                    async for line in resp.aiter_lines():
                        if line:
                            yield f"{line}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    # X-Accel-Buffering: no 让 nginx 对 SSE 关闭缓冲，否则流式被攒成批发，
    # 且推理模型静默思考超过 proxy_read_timeout 时连接会被掐断
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )

"""Requests in Traditional Chinese ("zht"), answered from the Simplified.

The routes that speak Chinese take lang=zh. A request with lang=zht, in the
query or in a JSON body (Ask, the trip plan), goes on as zh, and its JSON
answer comes back Traditional (knowledge/zh_hant.py). A question typed in
Traditional is turned Simplified first: Ask's Chinese matching is written in
Simplified. Every other request passes through untouched.

Installed innermost (main.py), so a body read here has already passed the
size limit, and a refusal's message (already in the visitor's language)
passes through here too.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qsl, urlencode

from app.knowledge.zh_hant import ZHT, simplified, traditional_tree

Message = dict[str, Any]


class TraditionalChinese:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        query = parse_qsl(scope.get("query_string", b"").decode("latin-1"), keep_blank_values=True)
        wanted = any(k == "lang" and v == ZHT for k, v in query)
        if wanted:
            plain = [(k, "zh" if k == "lang" and v == ZHT else v) for k, v in query]
            scope = {**scope, "query_string": urlencode(plain).encode("latin-1")}
        elif scope["method"] in ("POST", "PUT", "PATCH") and _content_type(scope["headers"]).startswith(b"application/json"):
            body = await _read(receive)
            body, wanted = _as_simplified(body)
            scope = {**scope, "headers": _with_length(scope["headers"], len(body))}
            receive = _replay(body, receive)
        if not wanted:
            await self.app(scope, receive, send)
            return
        await self.app(scope, receive, _traditional_json(send))


def _content_type(headers: list[tuple[bytes, bytes]]) -> bytes:
    for name, value in headers:
        if name.lower() == b"content-type":
            return value.lower()
    return b""


def _with_length(headers: list[tuple[bytes, bytes]], length: int) -> list[tuple[bytes, bytes]]:
    kept = [(n, v) for n, v in headers if n.lower() != b"content-length"]
    return [*kept, (b"content-length", str(length).encode())]


async def _read(receive: Any) -> bytes:
    chunks = []
    while True:
        message = await receive()
        if message["type"] != "http.request":
            break
        chunks.append(message.get("body", b""))
        if not message.get("more_body"):
            break
    return b"".join(chunks)


def _replay(body: bytes, receive: Any) -> Any:
    """The (rewritten) body once, then the client's own messages (a disconnect)."""
    sent = False

    async def replay() -> Message:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return await receive()

    return replay


def _as_simplified(body: bytes) -> tuple[bytes, bool]:
    try:
        data = json.loads(body)
    except ValueError:
        return body, False
    if not isinstance(data, dict) or data.get("lang") != ZHT:
        return body, False
    data["lang"] = "zh"
    if isinstance(data.get("question"), str):
        data["question"] = simplified(data["question"])
    return json.dumps(data, ensure_ascii=False).encode(), True


def _traditional_json(send: Any) -> Any:
    """`send`, with a JSON answer turned Traditional on its way out. Anything
    else (a stream, a photo) goes as it comes."""
    start: Message | None = None
    chunks: list[bytes] = []

    async def wrapped(message: Message) -> None:
        nonlocal start
        if message["type"] == "http.response.start":
            if _content_type(message.get("headers", [])).startswith(b"application/json"):
                start = message
                return
            await send(message)
            return
        if message["type"] != "http.response.body" or start is None:
            await send(message)
            return
        chunks.append(message.get("body", b""))
        if message.get("more_body"):
            return
        body = b"".join(chunks)
        try:
            body = json.dumps(traditional_tree(json.loads(body)), ensure_ascii=False, separators=(",", ":")).encode()
        except ValueError:
            pass
        await send({**start, "headers": _with_length(start.get("headers", []), len(body))})
        await send({"type": "http.response.body", "body": body, "more_body": False})

    return wrapped

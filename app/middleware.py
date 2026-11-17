"""Bound request bodies before JSON parsing, including chunked requests."""

import asyncio
from uuid import uuid4

from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings


class RequestLimits:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        raw_length = dict(scope.get("headers", [])).get(b"content-length")
        try:
            length = int(raw_length) if raw_length is not None else 0
            if length < 0:
                raise ValueError
        except ValueError:
            await self.reject(scope, receive, send, 400, "Invalid Content-Length")
            return
        if length > settings.max_request_bytes:
            await self.reject(scope, receive, send, 413, "Request body exceeds configured limit")
            return
        messages, size = [], 0
        try:
            async with asyncio.timeout(10):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    size += len(message.get("body", b""))
                    if size > settings.max_request_bytes:
                        await self.reject(
                            scope, receive, send, 413, "Request body exceeds configured limit"
                        )
                        return
                    messages.append(message)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            await self.reject(scope, receive, send, 408, "Request body timed out")
            return
        index = 0

        async def replay():
            nonlocal index
            if index < len(messages):
                message = messages[index]
                index += 1
                return message
            return await receive()

        await self.app(scope, replay, send)

    @staticmethod
    async def reject(scope, receive, send, status, message):
        request_id = str(uuid4())
        response = JSONResponse(
            status_code=status,
            content={
                "error": {
                    "code": "request_limit",
                    "message": message,
                    "details": [],
                    "request_id": request_id,
                }
            },
            headers={"X-Request-ID": request_id},
        )
        await response(scope, receive, send)

"""Normalizes every error response into the envelope documented in
docs/05-api-design.md Section 1: `{"error": {"code", "message", "details",
"request_id"}}`. Without this, FastAPI's default HTTPException handler wraps
our `detail={"code": ..., "message": ...}` payloads as `{"detail": {...}}`,
not `{"error": {...}}` — every raise HTTPException(...) call in this codebase
assumes the shape this module produces.
"""
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _envelope(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}, "request_id": f"req_{uuid.uuid4().hex[:12]}"}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            body = _envelope(exc.detail["code"], exc.detail.get("message", ""), exc.detail.get("details"))
        else:
            body = _envelope("INTERNAL_ERROR", str(exc.detail))
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # jsonable_encoder because pydantic v2 error dicts can carry a raw
        # exception instance in `ctx`, which plain json.dumps can't handle.
        errors = jsonable_encoder(exc.errors())
        return JSONResponse(status_code=422, content=_envelope("VALIDATION_ERROR", "Request validation failed.", {"errors": errors}))

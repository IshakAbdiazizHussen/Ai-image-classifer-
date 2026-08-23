"""One consistent error response shape across every endpoint (Phase 6
hardening): `{"error": {"code": "...", "message": "..."}}` for every
failure — a raised `APIError`, a bare `HTTPException`, a Pydantic request-
validation failure, or a genuinely unexpected exception. Routers raise
`APIError` with an explicit machine-readable `code`; everything else is
normalized here so a client never has to branch on which failure path
produced a response.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

# Fallback mapping for a plain HTTPException (no explicit code) raised
# somewhere outside our own APIError — keeps the response shape
# consistent even if a future route forgets to use APIError.
_CODE_BY_STATUS: dict[int, str] = {
    400: "bad_request",
    404: "not_found",
    413: "payload_too_large",
    422: "validation_error",
    429: "rate_limited",
    503: "service_unavailable",
}


class APIError(HTTPException):
    """Raise this instead of HTTPException for a stable, explicit
    machine-readable `code` alongside the human-readable message."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code


def _error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.detail),
            headers=exc.headers,
        )

    # Registered against Starlette's base HTTPException (not FastAPI's
    # subclass) because Starlette's own routing raises the BASE class
    # directly for things like an unmatched route (404) — a handler
    # registered only for the FastAPI subclass would never see those,
    # since exception-handler lookup walks up the MRO from the raised
    # instance, not down to subclasses. APIError (a subclass) still
    # correctly gets its own more specific handler above; exact-type
    # matches take priority over this fallback.
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = _CODE_BY_STATUS.get(exc.status_code, "error")
        return JSONResponse(
            status_code=exc.status_code, content=_error_body(code, str(exc.detail))
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_body("validation_error", "Request validation failed."),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Full traceback goes to the structured logger (server-side only);
        # the client only ever sees a generic message — never leak
        # internals (constraints.md rule 22's spirit: no sensitive detail
        # in anything client-visible).
        logger.exception("unhandled exception")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("internal_error", "An unexpected error occurred."),
        )

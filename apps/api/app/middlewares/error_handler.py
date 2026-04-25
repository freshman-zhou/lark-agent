from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from packages.shared.exceptions import AppException, ErrorCode
from packages.shared.logger import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException):
        logger.warning(
            "AppException: path=%s code=%s message=%s detail=%s",
            request.url.path,
            exc.code.value,
            exc.message,
            exc.detail,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_exception(request: Request, exc: RequestValidationError):
        logger.warning(
            "ValidationError: path=%s errors=%s",
            request.url.path,
            exc.errors(),
        )

        return JSONResponse(
            status_code=422,
            content={
                "code": ErrorCode.BAD_REQUEST.value,
                "message": "Request validation failed",
                "detail": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception):
        logger.exception(
            "Unhandled exception: path=%s error=%s",
            request.url.path,
            exc,
        )

        return JSONResponse(
            status_code=500,
            content={
                "code": ErrorCode.INTERNAL_ERROR.value,
                "message": "Internal server error",
                "detail": None,
            },
        )
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import __version__
from app.api import router
from app.repositories.case_repository import (
    CaseAlreadyExistsError,
    CaseNotFoundError,
    InvalidMarkdownError,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="200iq-moments",
        description="Local mistake case memory API",
        version=__version__,
    )
    app.include_router(router)
    return app


app = create_app()


@app.exception_handler(CaseNotFoundError)
async def case_not_found_handler(_, exc: CaseNotFoundError) -> JSONResponse:
    return error_response(404, "CASE_NOT_FOUND", f"Case not found: {exc}")


@app.exception_handler(CaseAlreadyExistsError)
async def case_already_exists_handler(_, exc: CaseAlreadyExistsError) -> JSONResponse:
    return error_response(409, "CASE_ALREADY_EXISTS", f"Case already exists: {exc}")


@app.exception_handler(InvalidMarkdownError)
async def invalid_markdown_handler(_, exc: InvalidMarkdownError) -> JSONResponse:
    return error_response(400, "INVALID_MARKDOWN", "Invalid markdown", {"warnings": exc.warnings})


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_, exc: RequestValidationError) -> JSONResponse:
    return error_response(
        422,
        "CASE_VALIDATION_ERROR",
        "Request validation failed",
        {"errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_, exc: Exception) -> JSONResponse:
    return error_response(500, "INTERNAL_ERROR", str(exc))


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        },
    )

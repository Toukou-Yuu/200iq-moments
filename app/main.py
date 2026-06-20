from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app import __version__
from app.api import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="200iq-moments",
        description="Local mistake case memory API",
        version=__version__,
    )
    app.include_router(router)
    return app


app = create_app()


@app.exception_handler(Exception)
async def unhandled_exception_handler(_, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc),
                "details": {},
            }
        },
    )

"""Public API application entrypoint."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.auth import AuthError, authenticate_request
from app.config import get_settings
from app.routes.auth import router as auth_router
from app.routes.integrations import router as integrations_router

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.include_router(auth_router)
app.include_router(integrations_router)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "api"}


@app.middleware("http")
async def require_session_cookie(request, call_next):
    if request.url.path.startswith("/api/"):
        try:
            authenticate_request(request, settings)
        except AuthError as exc:
            return JSONResponse(
                status_code=401,
                content={"detail": str(exc)},
            )
    return await call_next(request)

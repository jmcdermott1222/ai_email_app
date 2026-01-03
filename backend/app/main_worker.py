"""Worker application entrypoint."""

from fastapi import FastAPI

from app.config import get_settings

settings = get_settings()

app = FastAPI(title=f"{settings.app_name}-worker")


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "worker"}

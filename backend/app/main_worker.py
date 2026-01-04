"""Worker application entrypoint."""

from fastapi import Depends, FastAPI

from app.config import Settings, get_settings
from app.crypto import get_crypto
from app.db import get_db
from app.services.automation import snooze_sweep

settings = get_settings()

app = FastAPI(title=f"{settings.app_name}-worker")


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "worker"}


@app.post("/internal/jobs/snooze_sweep")
def run_snooze_sweep(
    settings: Settings = Depends(get_settings),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    crypto = get_crypto(settings)
    return snooze_sweep(db, settings, crypto)

"""Worker application entrypoint."""

from fastapi import Depends, FastAPI
from sqlalchemy import select

from app.config import Settings, get_settings
from app.crypto import get_crypto
from app.db import get_db
from app.models import Digest, User
from app.services.automation import snooze_sweep
from app.services.digest import default_since_ts, generate_daily_digest
from app.services.gmail_sync import full_sync_inbox

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


@app.post("/internal/jobs/digest_run")
def run_digest_job(
    settings: Settings = Depends(get_settings),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    crypto = get_crypto(settings)
    users = db.execute(select(User)).scalars().all()
    results = []
    for user in users:
        try:
            sync_result = full_sync_inbox(db, user.id, settings, crypto)
            latest = (
                db.execute(
                    select(Digest)
                    .where(Digest.user_id == user.id)
                    .order_by(Digest.created_at.desc())
                )
                .scalars()
                .first()
            )
            since_ts = default_since_ts(latest)
            digest = generate_daily_digest(db, settings, user.id, since_ts)
            results.append(
                {
                    "user_id": user.id,
                    "status": "ok",
                    "digest_id": digest.id,
                    "sync": {
                        "fetched": sync_result.fetched,
                        "upserted": sync_result.upserted,
                        "errors": sync_result.errors,
                    },
                }
            )
        except Exception as exc:
            db.rollback()
            results.append(
                {
                    "user_id": user.id,
                    "status": "error",
                    "error": str(exc),
                }
            )
    return {"status": "ok", "results": results}

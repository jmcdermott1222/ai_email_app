"""Queueing abstraction for background Gmail sync jobs."""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass

from app.config import Settings
from app.crypto import CryptoProvider
from app.services.gmail_sync import incremental_sync

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EnqueueResult:
    status: str
    detail: str
    task: dict | None = None


class LocalQueue:
    """Execute jobs synchronously in-process (local dev)."""

    def __init__(self, db, settings: Settings, crypto: CryptoProvider) -> None:
        self._db = db
        self._settings = settings
        self._crypto = crypto

    def enqueue_incremental_sync(self, user_id: int, history_id: str) -> EnqueueResult:
        incremental_sync(self._db, user_id, self._settings, self._crypto, history_id)
        return EnqueueResult(status="ok", detail="incremental sync executed")


class CloudTasksQueue:
    """Cloud Tasks stub that builds a request payload for a worker endpoint."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def enqueue_incremental_sync(self, user_id: int, history_id: str) -> EnqueueResult:
        queue_path = _queue_path(self._settings)
        target_url = self._settings.cloud_tasks_target_url.rstrip("/")
        if not queue_path or not target_url:
            raise ValueError("Cloud Tasks config is incomplete")

        payload = {"user_id": user_id, "history_id": history_id}
        body = json.dumps(payload).encode("utf-8")
        task = {
            "http_request": {
                "http_method": "POST",
                "url": f"{target_url}/internal/jobs/incremental_sync",
                "headers": {"Content-Type": "application/json"},
                "body": base64.b64encode(body).decode("utf-8"),
            }
        }
        if self._settings.cloud_tasks_service_account:
            task["http_request"]["oidc_token"] = {
                "service_account_email": self._settings.cloud_tasks_service_account
            }

        logger.warning(
            "Cloud Tasks enqueue stub invoked",
            extra={"queue": queue_path, "target_url": target_url},
        )
        return EnqueueResult(
            status="stub",
            detail="Cloud Tasks enqueue payload constructed (stub)",
            task={"queue_path": queue_path, "task": task},
        )


def enqueue_incremental_sync(
    db,
    settings: Settings,
    crypto: CryptoProvider,
    user_id: int,
    history_id: str,
) -> EnqueueResult:
    mode = (settings.queue_mode or "local").lower()
    if mode == "cloud_tasks":
        return CloudTasksQueue(settings).enqueue_incremental_sync(user_id, history_id)
    return LocalQueue(db, settings, crypto).enqueue_incremental_sync(
        user_id, history_id
    )


def _queue_path(settings: Settings) -> str:
    if (
        not settings.cloud_tasks_project
        or not settings.cloud_tasks_location
        or not settings.cloud_tasks_queue
    ):
        return ""
    return (
        "projects/"
        f"{settings.cloud_tasks_project}/locations/"
        f"{settings.cloud_tasks_location}/queues/"
        f"{settings.cloud_tasks_queue}"
    )

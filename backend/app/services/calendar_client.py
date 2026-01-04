"""Google Calendar API client wrapper."""

from __future__ import annotations

from googleapiclient.discovery import build


class CalendarClient:
    """Thin Calendar client wrapper for common operations."""

    def __init__(self, credentials, build_func=None) -> None:
        builder = build_func or build
        self._service = builder(
            "calendar",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

    def freebusy_query(self, time_min, time_max, calendar_ids=None):
        calendars = calendar_ids or ["primary"]
        return (
            self._service.freebusy()
            .query(
                body={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "items": [{"id": calendar_id} for calendar_id in calendars],
                }
            )
            .execute()
        )

    def create_event(self, calendar_id, event_body, send_updates="all"):
        return (
            self._service.events()
            .insert(
                calendarId=calendar_id,
                body=event_body,
                sendUpdates=send_updates,
            )
            .execute()
        )

    def list_calendars(self):
        return self._service.calendarList().list().execute()

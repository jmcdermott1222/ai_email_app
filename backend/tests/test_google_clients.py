"""Tests for Google API client wrappers."""

from unittest.mock import ANY, MagicMock

from app.services.calendar_client import CalendarClient
from app.services.gmail_client import GmailClient


def _build_service_mock():
    service = MagicMock()
    service.users.return_value = service
    service.messages.return_value = service
    service.threads.return_value = service
    service.drafts.return_value = service
    service.attachments.return_value = service
    service.labels.return_value = service
    service.freebusy.return_value = service
    service.events.return_value = service
    service.calendarList.return_value = service
    service.list.return_value = service
    service.get.return_value = service
    service.modify.return_value = service
    service.trash.return_value = service
    service.delete.return_value = service
    service.create.return_value = service
    service.query.return_value = service
    service.insert.return_value = service
    service.execute.return_value = {"ok": True}
    return service


def test_gmail_client_calls_build_and_list_messages(monkeypatch):
    service = _build_service_mock()
    build_mock = MagicMock(return_value=service)
    monkeypatch.setattr("app.services.gmail_client.build", build_mock)

    client = GmailClient(credentials=MagicMock())
    result = client.list_messages(q="is:unread", label_ids=["INBOX"], max_results=10)

    build_mock.assert_called_once_with(
        "gmail",
        "v1",
        credentials=ANY,
        cache_discovery=False,
    )
    service.list.assert_called_once_with(
        userId="me",
        q="is:unread",
        labelIds=["INBOX"],
        maxResults=10,
    )
    assert result == {"ok": True}


def test_gmail_client_create_draft(monkeypatch):
    service = _build_service_mock()
    build_mock = MagicMock(return_value=service)
    monkeypatch.setattr("app.services.gmail_client.build", build_mock)

    client = GmailClient(credentials=MagicMock())
    client.create_draft("raw-data", thread_id="thread-1")

    service.create.assert_called_once_with(
        userId="me",
        body={"message": {"raw": "raw-data", "threadId": "thread-1"}},
    )


def test_calendar_client_freebusy_query(monkeypatch):
    service = _build_service_mock()
    build_mock = MagicMock(return_value=service)
    monkeypatch.setattr("app.services.calendar_client.build", build_mock)

    client = CalendarClient(credentials=MagicMock())
    client.freebusy_query(
        "2024-01-01T00:00:00Z",
        "2024-01-02T00:00:00Z",
        calendar_ids=["primary", "work"],
    )

    build_mock.assert_called_once_with(
        "calendar",
        "v3",
        credentials=ANY,
        cache_discovery=False,
    )
    service.query.assert_called_once_with(
        body={
            "timeMin": "2024-01-01T00:00:00Z",
            "timeMax": "2024-01-02T00:00:00Z",
            "items": [{"id": "primary"}, {"id": "work"}],
        }
    )

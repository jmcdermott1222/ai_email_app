"""Gmail API client wrapper."""

from __future__ import annotations

from googleapiclient.discovery import build


class GmailClient:
    """Thin Gmail client wrapper for common operations."""

    def __init__(self, credentials, build_func=None) -> None:
        builder = build_func or build
        self._service = builder(
            "gmail",
            "v1",
            credentials=credentials,
            cache_discovery=False,
        )

    def list_messages(self, q=None, label_ids=None, max_results=50, page_token=None):
        params = {
            "userId": "me",
            "q": q,
            "labelIds": label_ids,
            "maxResults": max_results,
        }
        if page_token:
            params["pageToken"] = page_token
        return self._service.users().messages().list(**params).execute()

    def get_message(self, message_id, format="full"):
        return (
            self._service.users()
            .messages()
            .get(userId="me", id=message_id, format=format)
            .execute()
        )

    def get_thread(self, thread_id, format="full"):
        return (
            self._service.users()
            .threads()
            .get(userId="me", id=thread_id, format=format)
            .execute()
        )

    def modify_message_labels(
        self, message_id, add_label_ids=None, remove_label_ids=None
    ):
        return (
            self._service.users()
            .messages()
            .modify(
                userId="me",
                id=message_id,
                body={
                    "addLabelIds": add_label_ids or [],
                    "removeLabelIds": remove_label_ids or [],
                },
            )
            .execute()
        )

    def trash_message(self, message_id):
        return (
            self._service.users().messages().trash(userId="me", id=message_id).execute()
        )

    def delete_message(self, message_id):
        return (
            self._service.users()
            .messages()
            .delete(userId="me", id=message_id)
            .execute()
        )

    def create_draft(self, raw_mime_base64url, thread_id=None):
        message = {"raw": raw_mime_base64url}
        if thread_id:
            message["threadId"] = thread_id
        return (
            self._service.users()
            .drafts()
            .create(userId="me", body={"message": message})
            .execute()
        )

    def get_attachment(self, message_id, attachment_id):
        return (
            self._service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
            .execute()
        )

    def list_labels(self):
        return self._service.users().labels().list(userId="me").execute()

    def create_label(self, name):
        return (
            self._service.users()
            .labels()
            .create(userId="me", body={"name": name})
            .execute()
        )

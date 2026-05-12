"""Fetch new (unread) messages from Gmail.

Uses the Gmail REST API rather than IMAP; see docs/decisions/use_gmail_api.md
for the rationale. Gotchas captured in docs/api_notes.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator


@dataclass
class Message:
    id: str
    sender: str
    subject: str
    body: str
    thread: list[str]


def fetch_new_messages() -> Iterator[Message]:
    """Yield messages received since the last poll.

    The Gmail API uses historyId for incremental sync; we persist the last
    historyId between runs in .state/last_sync.json. See api_notes.md for
    edge cases (history expiry, partial pages).
    """
    # Stub for the demo. Real impl uses google-api-python-client.
    yield Message(
        id="demo-1",
        sender="alerts@datadog.com",
        subject="High CPU on api-prod-3",
        body="CPU sustained above 90% for 10 minutes.",
        thread=["original alert", "ack from oncall"],
    )

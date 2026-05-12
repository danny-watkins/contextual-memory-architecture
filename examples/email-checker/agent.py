"""Email checker agent — entrypoint.

Loop: fetch -> classify -> summarize (if long) -> notify.

See docs/architecture.md for the design rationale.
"""

from __future__ import annotations

import time

from skills.classify import classify_email
from skills.fetch_emails import fetch_new_messages
from skills.notify import route_notification
from skills.summarize import summarize_thread

POLL_INTERVAL_SECONDS = 300
LONG_THREAD_THRESHOLD = 6


def run_once() -> None:
    """One pass of the loop. Called on a timer in main()."""
    for msg in fetch_new_messages():
        category, confidence = classify_email(msg)
        summary = None
        if len(msg.thread) >= LONG_THREAD_THRESHOLD:
            summary = summarize_thread(msg.thread)
        route_notification(msg, category, confidence, summary)


def main() -> None:
    while True:
        try:
            run_once()
        except Exception as e:
            # Best-effort logging; don't crash the loop.
            print(f"[email-checker] iteration failed: {e}")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()

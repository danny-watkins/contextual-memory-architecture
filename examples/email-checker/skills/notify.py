"""Route notifications to the right channel based on category and confidence.

Channel routing rules: docs/decisions/notification_channels.md.
"""

from __future__ import annotations

CHANNEL_MAP = {
    "urgent_personal": "sms",
    "urgent_work": "slack_dm",
    "automated_alert": "slack_alerts_channel",
    "newsletter": "digest",
    "promo": "digest",
    "social": "digest",
    "spam": "drop",
    "other": "digest",
}


def route_notification(msg, category: str, confidence: float, summary: str | None) -> None:
    """Send notification to the channel determined by category."""
    channel = CHANNEL_MAP.get(category, "digest")
    if channel == "drop":
        return
    payload = {
        "subject": msg.subject,
        "from": msg.sender,
        "category": category,
        "confidence": confidence,
        "summary": summary,
    }
    _send(channel, payload)


def _send(channel: str, payload: dict) -> None:
    """Stub. Real impl dispatches to Slack SDK / Twilio / digest queue."""
    print(f"[notify:{channel}] {payload}")

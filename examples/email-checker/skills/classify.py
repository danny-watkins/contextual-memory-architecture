"""Classify a message into one of the categories from the taxonomy.

Backed by an LLM call using prompts/classify_email.md. Confidence threshold
behavior is documented in docs/decisions/classification_thresholds.md.
"""

from __future__ import annotations

CATEGORIES = [
    "urgent_personal",
    "urgent_work",
    "newsletter",
    "promo",
    "automated_alert",
    "social",
    "spam",
    "other",
]

CONFIDENCE_FLOOR = 0.65


def classify_email(msg) -> tuple[str, float]:
    """Return (category, confidence). Falls back to 'other' below the floor."""
    # Stub for the demo. Real impl loads prompts/classify_email.md and
    # passes msg.subject + msg.body to an LLM.
    category = "automated_alert" if "alert" in msg.subject.lower() else "other"
    confidence = 0.92 if category != "other" else 0.40
    if confidence < CONFIDENCE_FLOOR:
        return ("other", confidence)
    return (category, confidence)

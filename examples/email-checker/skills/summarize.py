"""Summarize a long email thread into 3-5 sentences.

Uses prompts/summarize_thread.md. Triggered when thread length exceeds
LONG_THREAD_THRESHOLD in agent.py.
"""

from __future__ import annotations


def summarize_thread(thread: list[str]) -> str:
    """Return a 3-5 sentence summary of the thread."""
    # Stub for the demo. Real impl renders prompts/summarize_thread.md with
    # the thread text and calls an LLM.
    return f"Thread of {len(thread)} messages; primary topic: alert acknowledgement."

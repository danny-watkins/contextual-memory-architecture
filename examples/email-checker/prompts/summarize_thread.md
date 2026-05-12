---
purpose: long-thread summarization prompt
output_format: prose
trigger: thread length >= LONG_THREAD_THRESHOLD (see agent.py)
---

# Summarize Thread

You will be given a sequence of messages forming an email thread. Produce a 3-5 sentence summary that captures:

1. The original ask or topic
2. The key decisions or commitments made
3. Any open questions or pending action items
4. Who currently owns the next step

## Style

- Past tense, neutral voice.
- Names, not pronouns, when more than two participants.
- If the thread is purely social or has no actionable content, say so in one sentence rather than padding.

## Constraints

- Do not invent details that are not in the thread.
- Do not summarize forwarded content unless it was actively discussed in the thread.
- If a participant explicitly asks for confidentiality (e.g., "this is between us"), do NOT include their name in the summary.

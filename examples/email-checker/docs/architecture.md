---
type: design_doc
status: current
last_revised: 2026-04-12
---

# Architecture

The agent is a stateless polling loop. Each iteration runs the same four-step pipeline; nothing about the design assumes continuous uptime.

## Pipeline

```
fetch_new_messages  -->  classify_email  -->  (summarize if long)  -->  route_notification
   (skills/fetch)        (skills/classify)        (skills/summarize)        (skills/notify)
```

The four steps live in `skills/` as independent modules so each can be tested and replaced in isolation. The orchestration logic in `agent.py` is intentionally thin (~30 lines).

## State

Persistent state lives in two places:

1. **Gmail's historyId**, persisted in `.state/last_sync.json`. Used by [[skills/fetch_emails]] for incremental sync.
2. **The user's labeling decisions** when a low-confidence message gets surfaced in the digest. These feed into [[decisions/classification_thresholds]] re-tuning.

No state lives in memory across iterations. A crash mid-loop means we re-process at most one message (idempotent at the notification layer via message id).

## LLM dependency

The classifier and summarizer both call an LLM. Provider is configured in `config/settings.yaml`. Failures fall back to:

- Classifier: returns `("other", 0.0)` and routes to digest
- Summarizer: returns the first message of the thread as the summary

## Why not IMAP

See [[decisions/use_gmail_api]]. Short version: history-based incremental sync, OAuth, structured labels.

## Failure modes

- **Rate limit**: Gmail API throttles at ~250 requests/sec/user. We poll at 5min so this is not a real concern; documented for future scale.
- **Token expiry**: OAuth refresh handled automatically by google-auth library.
- **LLM provider outage**: see fallbacks above. Notifications still go out, just less informative.

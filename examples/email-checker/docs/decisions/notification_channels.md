---
type: decision
status: accepted
date: 2026-03-22
confidence: 0.85
alternatives_considered: [single_channel, ml_routing, time_aware_routing]
---

# Decision: Map categories to fixed notification channels

## Context

Once a message is classified per [[../classification_taxonomy]], we need to decide HOW to notify the user. The agent supports four channels:

- **SMS** (Twilio) — interruptive, used sparingly
- **Slack DM** — interruptive during work hours
- **Slack alerts channel** — visible but not interruptive
- **Daily digest** — sent at 7am the next morning

## Decision

Static map from category to channel, defined in `CHANNEL_MAP` in [[../../skills/notify]]:

| Category          | Channel                |
|-------------------|------------------------|
| urgent_personal   | sms                    |
| urgent_work       | slack_dm               |
| automated_alert   | slack_alerts_channel   |
| newsletter        | digest                 |
| promo             | digest                 |
| social            | digest                 |
| spam              | drop (no notification) |
| other             | digest                 |

## Rationale

- **Determinism over cleverness.** A user shouldn't have to guess where a category will land. The map is in one place ([[../../skills/notify]]) and reads top-down.
- **Sleep protection.** Only `urgent_personal` (SMS) is allowed to bypass quiet hours. Everything else queues if it's outside 8am-10pm.
- **The "drop" outcome is intentional.** Spam shouldn't even hit the digest — it's noise.

## What we considered and rejected

- **ML-based routing**: train on user's response/dismissal patterns. Rejected — too much complexity for v1, and "the classifier was wrong" is a more common failure than "the routing was wrong."
- **Time-aware routing**: e.g., escalate `urgent_work` to SMS after midnight if unanswered. Rejected — out of scope; the user said they want a clean separation between work and after-hours.

## Status

Accepted. See [[classification_thresholds]] for how confidence affects whether the route fires at all.

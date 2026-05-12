---
type: reference
domain: classification
status: current
---

# Classification Taxonomy

Every incoming email lands in exactly one of the eight categories below. The set is closed — the classifier is not allowed to invent new categories. If a message doesn't fit cleanly, it goes to `other`.

## Categories

| Label             | Definition                                                                 | Example                          |
|-------------------|----------------------------------------------------------------------------|----------------------------------|
| urgent_personal   | Personal correspondence requiring same-day attention                       | Family member's medical update   |
| urgent_work       | Work message requiring response within business hours                      | Direct ask from manager          |
| automated_alert   | Machine-generated notification of a system event                           | Datadog alert, CI failure        |
| newsletter        | Recurring content from a subscribed sender                                 | Weekly tech digest               |
| promo             | Marketing or commercial offer                                              | Sale announcement                |
| social            | Notification from a social platform                                        | LinkedIn invitation              |
| spam              | Unsolicited and unwanted; should never trigger a notification              | Phishing attempt                 |
| other             | Anything that doesn't fit cleanly, or low-confidence classifications       | Confidence < 0.55                |

## Why this taxonomy

The categories map directly to notification channels (see [[decisions/notification_channels]]) and to the confidence-based routing rules in [[decisions/classification_thresholds]]. Adding a category means adding a channel route and re-tuning thresholds — non-trivial work, so we keep the set small.

## Examples and edge cases

- A vendor invoice from a known supplier: `urgent_work` (action required), not `automated_alert` (which is reserved for monitoring systems).
- A calendar invite: depends on the sender. From a colleague, `urgent_work`. From a service like Eventbrite, `social`.
- A password reset email you initiated: `automated_alert`.
- A password reset email you did NOT initiate: `urgent_personal` (potential account compromise).

---
type: reference
domain: gmail_api
last_revised: 2026-03-28
---

# Gmail API Notes

Operational notes from working with the Gmail REST API in [[skills/fetch_emails]]. See [[decisions/use_gmail_api]] for why we chose this over IMAP.

## Incremental sync via historyId

The cheap path is `users.history.list` with the last-known historyId. Returns only messages added/changed/deleted since that point.

Caveats:

- **History expires after 7 days** of inactivity. If we miss a week of polling, the historyId becomes invalid and we need to fall back to `users.messages.list` with a date filter.
- The `startHistoryId` is exclusive on the lower bound — pass the historyId you stored, not historyId+1.
- A response can be paginated; always exhaust `nextPageToken` before declaring sync complete.

## Threading

The API exposes thread membership via `threadId`. To fetch all messages in a thread, use `users.threads.get` rather than per-message lookups (one request vs. N).

## Labels vs. categories

Gmail's "Categories" (Primary, Social, Promotions, etc.) are exposed as system labels (`CATEGORY_SOCIAL`, etc.). These are useful as a soft prior for [[classification_taxonomy]] but should not override the LLM classifier.

## Rate limits

- 250 quota units/sec/user (one user = us)
- A `messages.get` is 5 units; a `messages.list` is 5 units; a `threads.get` is 10 units.

At our 5-minute poll cadence with ~50 new messages per poll, we're at <1% of quota.

## OAuth refresh

Tokens expire after 1 hour. The google-auth library refreshes automatically if you instantiate `Credentials` with a refresh_token. Do NOT manually refresh on every request.

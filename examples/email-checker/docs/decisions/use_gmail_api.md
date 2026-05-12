---
type: decision
status: accepted
date: 2026-02-15
confidence: 0.9
alternatives_considered: [imap, jmap]
---

# Decision: Use Gmail REST API instead of IMAP

## Context

Need to fetch new messages from the user's Gmail inbox. Options:

1. **IMAP** — universal protocol, supported by every mail provider
2. **Gmail REST API** — Google-specific, OAuth, structured responses
3. **JMAP** — modern replacement for IMAP, but Gmail doesn't support it

## Decision

Gmail REST API.

## Rationale

- **Incremental sync via historyId** is dramatically cheaper than IMAP's UIDNEXT polling. See [[../api_notes]] for the operational details.
- **OAuth** is what Google actively maintains; IMAP basic auth was deprecated for Gmail in 2022 and now requires app passwords (clunky for end users).
- **Structured labels and threading** in the JSON response — IMAP requires parsing RFC 5322 headers and doing client-side thread reconstruction.
- **Quota is generous** (see [[../api_notes]] section on rate limits) — at our scale, free.

## Tradeoffs

- **Lock-in to Gmail.** If we ever support other providers (Outlook, Fastmail), we'll need a provider abstraction layer. Out of scope for v1.
- **Library footprint.** `google-api-python-client` pulls in ~50MB of Google libraries. Acceptable for a long-running daemon; would matter for a serverless deployment.

## Status

Accepted. Implementation in [[../../skills/fetch_emails]].

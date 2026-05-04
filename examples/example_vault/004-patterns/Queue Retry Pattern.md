---
type: pattern
title: Queue Retry Pattern
domain: backend
status: active
confidence: 0.78
tags: [async, reliability, queue]
---

# Queue Retry Pattern

For external API calls that may fail intermittently, place the call behind an
async queue with bounded exponential backoff. Cap retries at N attempts and
route exhausted retries to a dead-letter queue.

Used by [[Async Capital Call Processing]].

See also: [[External API Synchronous Bottleneck]]

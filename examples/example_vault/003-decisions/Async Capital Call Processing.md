---
type: decision
title: Async Capital Call Processing
domain: backend
status: accepted
confidence: 0.86
tags: [capital-calls, performance, backend, async]
created: 2026-05-03
human_verified: true
---

# Async Capital Call Processing

We decided to move capital call processing out of the synchronous request path
and into an async queue.

This updates the prior synchronous design and uses the [[Queue Retry Pattern]].

Related pattern: [[External API Synchronous Bottleneck]]

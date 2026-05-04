---
type: pattern
title: External API Synchronous Bottleneck
domain: backend
status: active
confidence: 0.72
tags: [performance, anti-pattern, external-api]
---

# External API Synchronous Bottleneck

Synchronous calls to external APIs in the request path create a tail-latency
hazard: the slowest external dependency caps your service's latency.

Mitigation: see [[Queue Retry Pattern]].

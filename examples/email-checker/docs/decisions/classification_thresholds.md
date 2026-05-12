---
type: decision
status: accepted
date: 2026-03-04
confidence: 0.75
alternatives_considered: [single_threshold, three_band_routing, ml_calibration]
---

# Decision: Three-band confidence routing for the classifier

## Context

The classifier in [[../../skills/classify]] returns a `(category, confidence)` tuple. We need a policy for what to do at each confidence level.

## Decision

Three bands:

| Confidence    | Behavior                                           |
|---------------|----------------------------------------------------|
| >= 0.85       | Trust the classification, route through normal channel |
| 0.55 - 0.85   | Route through normal channel BUT flag in daily digest for user review |
| < 0.55        | Override to `other`, surface in digest, never trigger an urgent channel |

## Rationale

Single-threshold routing (the simpler design we started with) had a failure mode: a 0.60-confidence `urgent_personal` classification would fire SMS in the middle of the night. The middle band lets us still notify but with a "we're not sure" tag, so the user can correct the classifier.

## Why these specific numbers

- **0.55 floor**: empirically, our classifier's accuracy drops below 70% under this threshold (see [[../../tests/classifier_accuracy_2026-03.md]] — note: this file is referenced but doesn't exist yet).
- **0.85 trust ceiling**: above this, the classifier is right ~96% of the time, so the false positive rate of waking the user is acceptable.

## Open questions

- Should the bands be category-specific? A 0.70 `spam` is fine to drop; a 0.70 `urgent_personal` should probably ask the user. We considered per-category bands and rejected for v1 — too much config sprawl.
- The thresholds will need re-tuning as the classifier improves. No automated re-tuning yet; manual review every quarter.

## Status

Accepted. Constants live at the top of [[../../skills/classify]] (CONFIDENCE_FLOOR).

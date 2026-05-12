---
purpose: email classification prompt
output_format: json
categories_source: docs/classification_taxonomy.md
---

# Classify Email

Given an email's subject, sender, and body, return JSON:

```json
{
  "category": "<one of the categories from classification_taxonomy>",
  "confidence": <float 0.0-1.0>,
  "rationale": "<one sentence explaining the choice>"
}
```

## Inputs

- `from`: sender email
- `subject`: subject line
- `body`: first 2000 characters of body

## Categories

See [[classification_taxonomy]] for the full definitions. Use exactly one of the listed labels — do not invent new ones.

## Confidence calibration

- Above 0.85: high confidence, send through normal channel routing
- 0.55-0.85: send through routing but flag for review in the daily digest
- Below 0.55: classify as `other` and surface in the digest for the user to label

These thresholds come from [[decisions/classification_thresholds]].

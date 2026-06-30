# PayGuard AI — AI Governance Framework

## Overview

PayGuard AI is a proof-of-concept AI system designed to **support** human FWA investigators, not replace them. Every design decision prioritizes explainability, auditability, and human oversight.

---

## Core Governance Principles

### 1. Human-in-the-Loop (Required)

All PayGuard AI outputs are **recommendations for human review only**.

- No claim is autonomously denied, approved, or processed
- Every determination is explicitly labeled as "AI Recommendation"
- Human SIU investigator review is required before any action
- The system is positioned as decision-support, not decision-making

### 2. Data Privacy & PHI Protection

- **Synthetic data only** — no real Protected Health Information (PHI) used
- No patient identifiers, real provider NPI numbers, or actual claims data
- In production: all data would be processed in HIPAA-compliant infrastructure
- API calls to external LLMs would require BAA (Business Associate Agreement)
- No PII/PHI stored in session state or logs

### 3. Explainability & Transparency

- Every determination includes full chain-of-thought reasoning
- All CMS policy citations are surfaced with document IDs and URLs
- Confidence scores are provided with every recommendation
- Full audit trail exportable as PDF per claim
- No black-box decisions — every flag has a documented reason

### 4. Policy Grounding

- Agents query the live CMS Coverage API (api.coverage.cms.gov) in real-time
- Local guideline table provides verified policy content per CPT code
- All policy references include source document citations (NCD ID, LCD number)
- Policy content is versioned and traceable

### 5. Auditability

- Full agent reasoning logged per claim
- PDF audit reports generated with timestamps
- Session analytics track all analyzed claims
- In production: immutable audit log to database

---

## Known Limitations

| Limitation | Current State | Production Mitigation |
|---|---|---|
| String parsing | Substring matching for determination | Structured JSON outputs with Pydantic validation |
| CMS API | No caching, single fetch per session | Redis cache with TTL, retry logic |
| Batch processing | No rate limiting | Concurrency controls, max-row guards |
| Accuracy validation | 3 synthetic test cases only | Validation on historical claims with ground truth |
| Model drift | Not monitored | Scheduled re-evaluation against ground truth |
| Bias testing | Not performed | Demographic fairness analysis across provider types |

---

## Future Governance Controls

For production deployment in a real payer environment:

1. **Bias & Fairness Monitoring** — regular analysis of flag rates across provider demographics, specialties, and geographic regions
2. **False Positive Monitoring** — track and minimize inappropriate flags that could unfairly harm providers
3. **Model Drift Detection** — alert when model accuracy degrades vs. ground truth baseline
4. **HIPAA Infrastructure** — all data processing in HIPAA-compliant cloud environment with encryption at rest and in transit
5. **Regulatory Compliance** — alignment with CMS program integrity requirements, OIG guidelines
6. **Provider Appeal Process** — clear workflow for providers to dispute AI-flagged claims
7. **Model Card** — published documentation of training data, limitations, and performance characteristics

---

## Incident Response

In the event of system errors or unexpected outputs:

1. All automated recommendations halt
2. Claims route to human review queue
3. Incident logged with full context
4. Root cause analysis performed before system restart

---


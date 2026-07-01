# 🛡️ PayGuard AI

**Explainable Agentic AI for Healthcare Payment Integrity**

PayGuard AI is a proof-of-concept demonstrating how chain-of-thought reasoning across specialized AI agents can support — not replace — human FWA (Fraud, Waste, and Abuse) detection in healthcare payment integrity workflows.
🚀 **[Try the Live Demo](https://payguard-ai-jv5rvuxekszih7ewdxrlcr.streamlit.app)**
> ⚠️ **Important:** This system produces AI-assisted recommendations for human review only. No claim determination is made autonomously. All outputs require human SIU investigator validation before any action is taken.

---

## What It Does

PayGuard AI runs submitted healthcare claims through a 3-agent pipeline:

1. **Agent 1 — Clinical Necessity Review**: Assesses whether billed procedures are medically justified given the patient's clinical presentation, grounded in live CMS policy guidelines
2. **Agent 2 — FWA Pattern Detection**: Compares billed CPT codes against clinically justified procedures, flagging upcoding, unbundling, and phantom billing
3. **Agent 3 — Decision Synthesis**: Synthesizes both agents' findings into a plain-English recommendation for a human SIU investigator

---

## Quick Start

### 1. Clone the repository
```bash
git clone <repo-url>
cd payguard-ai
```

### 2. Create virtual environment
```bash
python -m venv venv

# Mac/Linux
source venv/bin/activate

# Windows (Git Bash)
source venv/Scripts/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

### 5. Run the application
```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Run Evaluation Harness

To validate system accuracy against ground-truth synthetic cases:

```bash
python evaluation.py
```

Expected output:
```
PayGuard AI — Evaluation Harness
==================================
CLM-2025-001 | Expected: UPCODING        | Got: DENY WITH CAUSE  | ✓ PASS
CLM-2025-002 | Expected: SERVICES_NOT_RENDERED | Got: FLAG FOR REVIEW | ✓ PASS
CLM-2025-003 | Expected: CLEAN           | Got: APPROVE          | ✓ PASS

Accuracy: 3/3 (100.0%)
```

---

## Project Structure

```
payguard-ai/
├── app.py                    # Streamlit UI (main application)
├── orchestrator.py           # Agent pipeline orchestration
├── evaluation.py             # Accuracy evaluation harness
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── .env.example              # Environment variable template
├── .gitignore                # Git ignore rules
├── agents/
│   ├── clinical_agent.py     # Agent 1: Clinical necessity review
│   ├── fwa_agent.py          # Agent 2: FWA pattern detection
│   └── decision_agent.py     # Agent 3: Decision synthesis (structured output)
├── data/
│   ├── synthetic_claims.json # Ground-truth test cases
│   └── cms_guidelines.py     # CMS policy reference data
└── utils/
    ├── prompts.py            # Agent prompt templates
    ├── cms_api.py            # Live CMS Coverage API integration
    ├── provider_risk.py      # Provider risk scoring engine
    └── pdf_export.py         # Audit report PDF generation
```

---

## AI Governance

PayGuard AI was designed with the following governance principles:

- **Synthetic data only** — no real PHI used anywhere in development or demo
- **Human-in-the-loop required** — all outputs are recommendations, not autonomous decisions
- **Explainability first** — every determination includes full reasoning chain and CMS citations
- **Policy grounded** — agents query live CMS Coverage API (api.coverage.cms.gov) for NCD/LCD references
- **Audit trail** — full agent reasoning is logged and exportable as PDF audit reports
- **No autonomous denial** — the system flags claims for human SIU review, never denies independently
- **Future work**: bias testing, false-positive monitoring, model drift detection, HIPAA-compliant infrastructure

---

## Technology Stack

| Component | Technology |
|---|---|
| LLM Backend | OpenAI GPT-4o-mini |
| Agent Framework | Custom 3-agent pipeline |
| Policy Grounding | Live CMS Coverage API + curated guidelines |
| UI | Streamlit |
| PDF Export | ReportLab |
| Structured Outputs | Pydantic v2 |
| Data Validation | JSON schema |

---

## Limitations & Known Issues

- **String parsing**: Agent outputs are currently parsed via substring matching. Production version would use OpenAI structured JSON outputs with Pydantic validation.
- **CMS API**: NCD list is fetched per session with no caching. Production would cache with TTL.
- **Batch processing**: No rate limiting on batch tab. Production would implement concurrency controls.
- **Accuracy**: Validated only on 3 synthetic cases. Production would require validation on historical claims with known ground truth.

---

## Built By

**Neha Save** 

---

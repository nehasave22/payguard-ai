"""
Agent 3 — Decision Synthesis
==============================
Uses OpenAI structured JSON output (JSON mode) with Pydantic validation
to produce reliable, parseable determinations instead of brittle string parsing.
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from utils.prompts import DECISION_AGENT_PROMPT

load_dotenv()


# ── Pydantic schema for structured output ─────────────────────────────────────
class FWAFlag(BaseModel):
    cpt_code: str = Field(description="The CPT code being flagged")
    anomaly_type: str = Field(description="Type of anomaly: UPCODING, UNBUNDLING, SERVICES_NOT_RENDERED, MEDICALLY_UNNECESSARY")
    reason: str = Field(description="Plain English reason for the flag")
    policy_reference: Optional[str] = Field(default=None, description="CMS policy document referenced")


class ClaimDetermination(BaseModel):
    determination: str = Field(
        description="Final determination: APPROVE, FLAG_FOR_REVIEW, or DENY_WITH_CAUSE"
    )
    confidence_score: int = Field(
        description="Confidence in determination 0-100",
        ge=0, le=100
    )
    confidence_reason: str = Field(
        description="Brief reason for this confidence level"
    )
    executive_summary: str = Field(
        description="2-3 sentence plain English summary for SIU investigator"
    )
    detailed_reasoning: str = Field(
        description="Full explanation referencing clinical findings and CMS guidelines"
    )
    recommended_action: str = Field(
        description="Concrete next steps for the SIU team"
    )
    estimated_recoverable_amount: int = Field(
        description="Estimated recoverable amount in dollars (0 if APPROVE)",
        ge=0
    )
    flags_summary: list[FWAFlag] = Field(
        default=[],
        description="List of specific FWA flags detected"
    )

    @field_validator("determination")
    @classmethod
    def validate_determination(cls, v):
        valid = {"APPROVE", "FLAG_FOR_REVIEW", "DENY_WITH_CAUSE"}
        v_upper = v.upper().replace(" ", "_")
        if v_upper not in valid:
            # Handle legacy string formats
            if "APPROVE" in v_upper:
                return "APPROVE"
            elif "FLAG" in v_upper:
                return "FLAG_FOR_REVIEW"
            else:
                return "DENY_WITH_CAUSE"
        return v_upper

    def to_display_determination(self) -> str:
        """Convert internal format to display format."""
        mapping = {
            "APPROVE": "APPROVE",
            "FLAG_FOR_REVIEW": "FLAG FOR REVIEW",
            "DENY_WITH_CAUSE": "DENY WITH CAUSE",
        }
        return mapping.get(self.determination, self.determination)


DECISION_STRUCTURED_PROMPT = """
You are a senior claims adjudication AI. Review the clinical and FWA analysis
and produce a structured JSON determination for a human SIU investigator.

Clinical Review Summary:
{clinical_summary}

FWA Detection Summary:
{fwa_summary}

Claim Information:
- Case ID: {case_id}
- Provider: {provider_name}
- Billed Amount: ${billed_amount}

IMPORTANT: Respond ONLY with valid JSON matching this exact schema:
{{
  "determination": "APPROVE" | "FLAG_FOR_REVIEW" | "DENY_WITH_CAUSE",
  "confidence_score": <integer 0-100>,
  "confidence_reason": "<brief reason for confidence level>",
  "executive_summary": "<2-3 sentences for SIU investigator>",
  "detailed_reasoning": "<full explanation with CMS citations>",
  "recommended_action": "<concrete next steps for SIU team>",
  "estimated_recoverable_amount": <integer dollars, 0 if APPROVE>,
  "flags_summary": [
    {{
      "cpt_code": "<code>",
      "anomaly_type": "<UPCODING|UNBUNDLING|SERVICES_NOT_RENDERED|MEDICALLY_UNNECESSARY>",
      "reason": "<plain English reason>",
      "policy_reference": "<CMS NCD/LCD reference or null>"
    }}
  ]
}}

Do not include any text outside the JSON object.
"""


def run_decision_agent(case: dict, clinical_summary: str, fwa_summary: str) -> str:
    """
    Run Agent 3 with structured JSON output.
    Returns formatted text for display (backward compatible with app.py).
    Also stores structured data on the case dict for downstream use.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = DECISION_STRUCTURED_PROMPT.format(
        clinical_summary=clinical_summary,
        fwa_summary=fwa_summary,
        case_id=case.get("case_id", "UNKNOWN"),
        provider_name=case.get("provider_name", "Unknown"),
        billed_amount=case.get("billed_amount", 0)
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior claims adjudication AI. "
                        "Always respond with valid JSON only. "
                        "No preamble, no markdown, no explanation outside JSON."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            response_format={"type": "json_object"}  # OpenAI JSON mode
        )

        raw_json = response.choices[0].message.content

        # Parse and validate with Pydantic
        data = json.loads(raw_json)
        det = ClaimDetermination(**data)

        # Store structured result on case for evaluation harness
        case["_structured_determination"] = det

        # Convert to display text (backward compatible with app.py parsing)
        display_text = _format_for_display(det, case)
        return display_text

    except Exception as e:
        # Fallback to unstructured prompt if JSON mode fails
        print(f"[Decision Agent] Structured output failed ({e}), falling back to text mode")
        return _fallback_text_mode(client, case, clinical_summary, fwa_summary)


def _format_for_display(det: ClaimDetermination, case: dict) -> str:
    """Format structured determination as readable text for the UI."""
    display_det = det.to_display_determination()

    flags_text = ""
    if det.flags_summary:
        flags_text = "\nFLAGS DETECTED:\n"
        for flag in det.flags_summary:
            ref = f" | Policy: {flag.policy_reference}" if flag.policy_reference else ""
            flags_text += f"- {flag.cpt_code} | {flag.anomaly_type} | {flag.reason}{ref}\n"
    else:
        flags_text = "\nFLAGS DETECTED:\nNo anomalies detected.\n"

    return f"""FINAL DETERMINATION: {display_det}

CONFIDENCE SCORE: {det.confidence_score}
{det.confidence_reason}

EXECUTIVE SUMMARY:
{det.executive_summary}

DETAILED REASONING:
{det.detailed_reasoning}
{flags_text}
RECOMMENDED ACTION:
{det.recommended_action}

ESTIMATED RECOVERABLE AMOUNT: ${det.estimated_recoverable_amount:,}"""


def _fallback_text_mode(client, case, clinical_summary, fwa_summary) -> str:
    """Fallback to unstructured text if JSON mode unavailable."""
    prompt = DECISION_AGENT_PROMPT.format(
        clinical_summary=clinical_summary,
        fwa_summary=fwa_summary,
        case_id=case.get("case_id", "UNKNOWN"),
        provider_name=case.get("provider_name", "Unknown"),
        billed_amount=case.get("billed_amount", 0)
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a senior claims adjudication AI. Write clear, professional determinations."
            },
            {"role": "user", "content": prompt}
        ],
        max_tokens=1024
    )
    return response.choices[0].message.content
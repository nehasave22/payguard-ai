import os
from openai import OpenAI
from dotenv import load_dotenv
from utils.prompts import CLINICAL_AGENT_PROMPT
from data.cms_guidelines import get_relevant_guidelines

load_dotenv()

def run_clinical_agent(case: dict) -> str:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # ── Handle missing vitals ─────────────────────────────────────────────────
    vitals = case.get("vitals", "Not recorded")
    if not vitals or vitals.strip().lower() in ["not recorded", "none", "", "n/a"]:
        vitals = "Not recorded"
        vitals_note = (
            "IMPORTANT: Vitals are not documented for this claim. "
            "Explicitly note this absence in your clinical reasoning. "
            "For high-complexity billed services (e.g. CPT 99215, 99223), "
            "missing vitals is itself a documentation red flag per CMS E/M guidelines, "
            "which require comprehensive documentation to support complex billing codes."
        )
    else:
        vitals_note = "Vitals are documented and should be used to assess clinical severity."

    # ── Get CMS guidelines for submitted CPT codes ────────────────────────────
    cms_context = get_relevant_guidelines(case.get("submitted_cpt_codes", []))

    # ── Build prompt ──────────────────────────────────────────────────────────
    prompt = CLINICAL_AGENT_PROMPT.format(
        age=case.get("patient_age", "Unknown"),
        gender=case.get("patient_gender", "Unknown"),
        complaint=case.get("chief_complaint", "Not specified"),
        history=case.get("diagnosis_history", "Not specified"),
        vitals=vitals,
        vitals_note=vitals_note,
        icd_codes=", ".join(case.get("submitted_icd_codes", [])),
        cms_guidelines=cms_context
    )

    # ── Call OpenAI ───────────────────────────────────────────────────────────
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a clinical medical reviewer AI in a healthcare payment integrity system. "
                    "Be precise, evidence-based, and structured. "
                    "Always cite CMS guidelines when making determinations. "
                    "Always explicitly address missing or abnormal documentation."
                )
            },
            {"role": "user", "content": prompt}
        ],
        max_tokens=1024
    )

    return response.choices[0].message.content
"""
PayGuard AI — Policy-to-Rule Engine
=====================================
Converts plain-English CMS policy statements into structured,
executable deterministic rules that pre-screen claims BEFORE
the LLM agents run.

This is the hybrid LLM-plus-deterministic approach used in
real payment integrity systems — fast rule-based pre-screening
catches obvious violations instantly, while LLM agents handle
nuanced cases that require clinical reasoning.

Architecture:
  Claim Input
      ↓
  [Policy Rules Engine]  ← deterministic, instant, auditable
      ↓ pre-screen result
  [LLM Agent Pipeline]   ← nuanced reasoning for edge cases
      ↓
  Final Recommendation
"""

from dataclasses import dataclass, field
from typing import Optional
import json


# ── Rule Data Model ───────────────────────────────────────────────────────────

@dataclass
class PolicyRule:
    """A single executable policy rule derived from CMS written policy."""
    rule_id:          str
    name:             str
    source_policy:    str          # Original plain-English CMS policy text
    source_document:  str          # CMS document ID (NCD/LCD)
    source_url:       str          # CMS document URL
    cpt_codes:        list         # CPT codes this rule applies to
    icd_exclusions:   list         # ICD codes that would INVALIDATE billing
    red_flags:        list         # Clinical indicators that justify the procedure
    min_conservative_weeks: Optional[int]  # Weeks of conservative treatment required
    requires_prior_imaging: bool   # Whether prior imaging must be documented
    complexity_required:    str    # "low" | "moderate" | "high" | "any"
    action:           str          # "APPROVE" | "FLAG" | "DENY"
    explanation:      str          # Plain-English explanation for SIU

    def to_dict(self) -> dict:
        return {
            "rule_id":          self.rule_id,
            "name":             self.name,
            "source_policy":    self.source_policy,
            "source_document":  self.source_document,
            "source_url":       self.source_url,
            "cpt_codes":        self.cpt_codes,
            "action":           self.action,
            "explanation":      self.explanation
        }


@dataclass
class RuleEvaluation:
    """Result of evaluating a claim against policy rules."""
    rule_id:        str
    rule_name:      str
    cpt_code:       str
    triggered:      bool           # Did this rule fire?
    action:         str            # APPROVE | FLAG | DENY
    confidence:     int            # 0-100 deterministic confidence
    reason:         str            # Human-readable reason
    source_policy:  str            # Original policy text
    source_document:str
    source_url:     str


@dataclass
class PreScreenResult:
    """Complete pre-screen result for a claim."""
    case_id:         str
    evaluations:     list          # List of RuleEvaluation
    triggered_rules: list          # Rules that fired
    pre_screen_flag: str           # PASS | FLAG | DENY
    violations:      list          # Specific violations found
    summary:         str           # Human-readable summary
    send_to_agents:  bool          # Whether LLM agents should run


# ── CMS Policy Rules Library ──────────────────────────────────────────────────
# Each rule is derived directly from CMS LCD/NCD written policy

POLICY_RULES = [

    PolicyRule(
        rule_id="MRI_LUMBAR_001",
        name="MRI Lumbar Spine — Conservative Treatment Requirement",
        source_policy=(
            "An MRI of the lumbar spine is covered only when the patient has "
            "not responded to a reasonable trial of conservative treatment "
            "lasting at least 4-6 weeks, unless red-flag conditions are present "
            "such as suspected tumor, infection, fracture, or neurological deficits."
        ),
        source_document="CMS LCD L34220",
        source_url="https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=34220",
        cpt_codes=["72148", "72149", "72158"],
        icd_exclusions=[],
        red_flags=[
            "neurological_deficit", "suspected_malignancy", "fracture",
            "infection", "bladder_bowel_dysfunction", "progressive_weakness"
        ],
        min_conservative_weeks=4,
        requires_prior_imaging=False,
        complexity_required="any",
        action="FLAG",
        explanation=(
            "MRI lumbar spine requires documented failure of conservative treatment "
            "for at least 4 weeks, or presence of red-flag symptoms. "
            "Billing without this documentation is not covered under CMS LCD L34220."
        )
    ),

    PolicyRule(
        rule_id="KNEE_ARTHROPLASTY_001",
        name="Total Knee Arthroplasty — Diagnosis Mismatch",
        source_policy=(
            "Total knee arthroplasty (CPT 27447) is covered for severe osteoarthritis "
            "with documented failure of conservative treatment and significant functional "
            "limitation. It requires prior imaging showing joint pathology and is not "
            "appropriate for back pain diagnoses or non-knee conditions."
        ),
        source_document="CMS LCD L38548",
        source_url="https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=38548",
        cpt_codes=["27447", "27446", "27448"],
        icd_exclusions=["M54.5", "M54.4", "M54.3", "M54.2"],  # Back pain codes
        red_flags=[],
        min_conservative_weeks=None,
        requires_prior_imaging=True,
        complexity_required="any",
        action="DENY",
        explanation=(
            "Total knee arthroplasty cannot be billed with back pain ICD codes. "
            "This procedure requires documented knee pathology with prior imaging. "
            "Billing CPT 27447 for a back pain patient is a clear services-not-rendered violation."
        )
    ),

    PolicyRule(
        rule_id="ECHOCARDIOGRAPHY_001",
        name="Echocardiography — Cardiac Symptom Requirement",
        source_policy=(
            "Transthoracic echocardiography (CPT 93306) is covered for evaluation of "
            "cardiac structure and function, valvular disease, heart failure, or "
            "endocarditis. It is not appropriate as routine screening without "
            "documented cardiac symptoms or clinical indication."
        ),
        source_document="CMS NCD 20.7",
        source_url="https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=98",
        cpt_codes=["93306", "93307", "93308"],
        icd_exclusions=["Z00.00", "Z00.01", "Z01.89"],  # Routine wellness codes
        red_flags=["chest_pain", "dyspnea", "palpitations", "syncope", "heart_failure"],
        min_conservative_weeks=None,
        requires_prior_imaging=False,
        complexity_required="any",
        action="FLAG",
        explanation=(
            "Echocardiography billed alongside wellness visit ICD codes "
            "lacks clinical justification per CMS NCD 20.7. "
            "This procedure requires documented cardiac symptoms or indication."
        )
    ),

    PolicyRule(
        rule_id="MRI_BRAIN_001",
        name="MRI Brain — Neurological Indication Requirement",
        source_policy=(
            "MRI of the brain (CPT 70553) is covered for evaluation of neurological "
            "symptoms, seizures, suspected malignancy, dementia workup, or multiple "
            "sclerosis. It is not appropriate for routine wellness visits without "
            "documented neurological complaints or clinical indication."
        ),
        source_document="CMS NCD 220.2",
        source_url="https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=177",
        cpt_codes=["70553", "70551", "70552"],
        icd_exclusions=["Z00.00", "Z00.01"],  # Routine wellness
        red_flags=["neurological_symptoms", "seizure", "suspected_malignancy",
                   "dementia", "multiple_sclerosis", "headache_severe"],
        min_conservative_weeks=None,
        requires_prior_imaging=False,
        complexity_required="any",
        action="FLAG",
        explanation=(
            "Brain MRI billed alongside routine wellness ICD codes is not covered "
            "per CMS NCD 220.2. Neurological symptoms or clinical indication required."
        )
    ),

    PolicyRule(
        rule_id="EM_COMPLEXITY_001",
        name="E/M High Complexity — Documentation Requirement",
        source_policy=(
            "CPT 99215 (high complexity office visit) requires medically appropriate "
            "history, examination, and high complexity medical decision making, OR "
            "40-54 minutes of total time. It is not appropriate for straightforward "
            "acute complaints or routine follow-up visits."
        ),
        source_document="CMS E/M Guidelines 2023",
        source_url="https://www.cms.gov/medicare/physician-fee-schedule/em-office-visits",
        cpt_codes=["99215"],
        icd_exclusions=["M54.5", "Z00.00", "J06.9", "M25.561"],  # Simple conditions
        red_flags=["multiple_chronic_conditions", "high_complexity_mdm"],
        min_conservative_weeks=None,
        requires_prior_imaging=False,
        complexity_required="high",
        action="FLAG",
        explanation=(
            "CPT 99215 (high complexity) billed with simple acute or wellness ICD codes "
            "is not supported by CMS E/M guidelines. High complexity requires documented "
            "MDM or 40+ minutes of physician time."
        )
    ),

    PolicyRule(
        rule_id="PHYSICAL_THERAPY_001",
        name="Physical Therapy — Self-Limiting Condition",
        source_policy=(
            "Physical therapy evaluation (CPT 97001) requires documented functional "
            "limitation with measurable therapy goals and physician referral. "
            "It is not appropriate for self-limiting acute conditions expected "
            "to resolve within days without specific functional deficits."
        ),
        source_document="CMS LCD L33865",
        source_url="https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=33865",
        cpt_codes=["97001", "97002"],
        icd_exclusions=[],
        red_flags=["functional_limitation", "chronic_condition", "post_surgical"],
        min_conservative_weeks=None,
        requires_prior_imaging=False,
        complexity_required="any",
        action="FLAG",
        explanation=(
            "Physical therapy evaluation requires documented functional limitation "
            "and measurable therapy goals per CMS LCD L33865. "
            "Not appropriate for acute self-limiting conditions."
        )
    ),

]


# ── Rule Evaluation Engine ────────────────────────────────────────────────────

def extract_clinical_signals(case: dict) -> dict:
    """
    Extract clinical signals from the claim for rule evaluation.
    Uses keyword matching on complaint and history fields.
    """
    complaint = (case.get("chief_complaint","") + " " +
                 case.get("diagnosis_history","")).lower()

    return {
        "has_neurological_deficit": any(w in complaint for w in
            ["neurological","weakness","numbness","tingling","paralysis",
             "deficit","radiating","nerve"]),
        "has_cardiac_symptoms": any(w in complaint for w in
            ["chest pain","palpitation","dyspnea","shortness of breath",
             "syncope","heart failure","arrhythmia"]),
        "has_knee_pathology": any(w in complaint for w in
            ["knee","osteoarthritis","joint","meniscus","ligament"]),
        "is_self_limiting": any(w in complaint for w in
            ["resolved","improving","mild","minor","brief",
             "ibuprofen","over the counter","otc"]),
        "is_routine_wellness": any(w in complaint for w in
            ["routine","wellness","annual","checkup","no complaints",
             "feeling well","no acute"]),
        "has_functional_limitation": any(w in complaint for w in
            ["functional","limitation","unable","difficulty","restricted",
             "cannot","mobility"]),
        "duration_days": _extract_duration(complaint),
    }


def _extract_duration(text: str) -> int:
    """Extract symptom duration in days from complaint text."""
    import re
    # Look for patterns like "3 days", "2 weeks", "1 month"
    day_match   = re.search(r'(\d+)\s*day', text)
    week_match  = re.search(r'(\d+)\s*week', text)
    month_match = re.search(r'(\d+)\s*month', text)

    if month_match: return int(month_match.group(1)) * 30
    if week_match:  return int(week_match.group(1)) * 7
    if day_match:   return int(day_match.group(1))
    return 0


def evaluate_rule(rule: PolicyRule, case: dict, signals: dict) -> RuleEvaluation:
    """
    Evaluate a single policy rule against a claim.
    Returns deterministic pass/flag/deny result.
    """
    cpt_codes = case.get("submitted_cpt_codes", [])
    icd_codes = case.get("submitted_icd_codes", [])

    # Check if rule applies to any billed CPT code
    applicable_codes = [c for c in cpt_codes if c in rule.cpt_codes]
    if not applicable_codes:
        return RuleEvaluation(
            rule_id=rule.rule_id, rule_name=rule.name,
            cpt_code="N/A", triggered=False, action="PASS",
            confidence=100, reason="Rule does not apply to billed codes.",
            source_policy=rule.source_policy,
            source_document=rule.source_document,
            source_url=rule.source_url
        )

    cpt_code = applicable_codes[0]

    # ── Check ICD exclusions ──────────────────────────────────────────────────
    # If billed ICD code is in the exclusion list, this is a clear violation
    icd_violations = [icd for icd in icd_codes if icd in rule.icd_exclusions]
    if icd_violations:
        return RuleEvaluation(
            rule_id=rule.rule_id, rule_name=rule.name,
            cpt_code=cpt_code, triggered=True,
            action=rule.action, confidence=95,
            reason=(
                f"CPT {cpt_code} billed with incompatible ICD code(s) "
                f"{', '.join(icd_violations)}. "
                f"{rule.explanation}"
            ),
            source_policy=rule.source_policy,
            source_document=rule.source_document,
            source_url=rule.source_url
        )

    # ── Check conservative treatment duration for imaging ─────────────────────
    if rule.min_conservative_weeks and not signals.get("has_neurological_deficit"):
        duration_days = signals.get("duration_days", 0)
        required_days = rule.min_conservative_weeks * 7
        if 0 < duration_days < required_days:
            return RuleEvaluation(
                rule_id=rule.rule_id, rule_name=rule.name,
                cpt_code=cpt_code, triggered=True,
                action=rule.action, confidence=85,
                reason=(
                    f"CPT {cpt_code}: Symptom duration ({duration_days} days) "
                    f"is less than the required {required_days} days of conservative "
                    f"treatment per {rule.source_document}. "
                    f"No red-flag conditions documented."
                ),
                source_policy=rule.source_policy,
                source_document=rule.source_document,
                source_url=rule.source_url
            )

    # ── Check wellness + imaging mismatch ─────────────────────────────────────
    wellness_icds = ["Z00.00", "Z00.01", "Z01.89"]
    is_wellness = any(icd in wellness_icds for icd in icd_codes)
    imaging_cpts = ["72148","70553","93306","70551","70552","72149"]
    is_imaging = cpt_code in imaging_cpts

    if is_wellness and is_imaging:
        return RuleEvaluation(
            rule_id=rule.rule_id, rule_name=rule.name,
            cpt_code=cpt_code, triggered=True,
            action="FLAG", confidence=90,
            reason=(
                f"CPT {cpt_code} (imaging/diagnostic procedure) billed "
                f"alongside routine wellness ICD codes. "
                f"Clinical indication required per {rule.source_document}."
            ),
            source_policy=rule.source_policy,
            source_document=rule.source_document,
            source_url=rule.source_url
        )

    # ── No violation detected ─────────────────────────────────────────────────
    return RuleEvaluation(
        rule_id=rule.rule_id, rule_name=rule.name,
        cpt_code=cpt_code, triggered=False,
        action="PASS", confidence=80,
        reason=f"CPT {cpt_code} passes rule check for {rule.name}.",
        source_policy=rule.source_policy,
        source_document=rule.source_document,
        source_url=rule.source_url
    )


def run_pre_screen(case: dict) -> PreScreenResult:
    """
    Run all policy rules against a claim deterministically.
    This runs BEFORE the LLM agents for fast, auditable pre-screening.
    """
    signals     = extract_clinical_signals(case)
    evaluations = []
    violations  = []

    for rule in POLICY_RULES:
        result = evaluate_rule(rule, case, signals)
        evaluations.append(result)
        if result.triggered:
            violations.append(result)

    # Determine overall pre-screen flag
    if any(v.action == "DENY" for v in violations):
        pre_screen_flag = "DENY"
    elif violations:
        pre_screen_flag = "FLAG"
    else:
        pre_screen_flag = "PASS"

    # Build summary
    if not violations:
        summary = (
            f"Pre-screen PASSED — no deterministic policy violations detected "
            f"across {len(POLICY_RULES)} CMS rules. "
            f"Sending to LLM agent pipeline for nuanced clinical review."
        )
    else:
        viol_list = ", ".join([f"CPT {v.cpt_code} ({v.rule_id})" for v in violations])
        summary = (
            f"Pre-screen FLAGGED — {len(violations)} deterministic rule violation(s) "
            f"detected: {viol_list}. "
            f"LLM agents will provide detailed reasoning."
        )

    return PreScreenResult(
        case_id=case.get("case_id","UNKNOWN"),
        evaluations=evaluations,
        triggered_rules=violations,
        pre_screen_flag=pre_screen_flag,
        violations=violations,
        summary=summary,
        send_to_agents=True  # Always send to agents for full reasoning
    )


# ── Policy-to-Rule Converter (LLM-assisted) ───────────────────────────────────

def convert_policy_text_to_rule(policy_text: str, cpt_code: str,
                                  source_doc: str) -> dict:
    """
    Uses GPT to convert a plain-English CMS policy statement
    into a structured executable rule definition.

    This demonstrates the "policy-to-programming" capability
    described in Topic 3 of the Cotiviti assessment.
    """
    import os
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv()

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = f"""
You are a healthcare payment integrity engineer converting CMS policy text
into structured executable rules for a claims pre-screening system.

Convert this CMS policy statement into a JSON rule definition:

Policy Text: "{policy_text}"
CPT Code: {cpt_code}
Source Document: {source_doc}

Respond ONLY with valid JSON matching this schema:
{{
  "rule_id": "<SNAKE_CASE_ID>",
  "name": "<Short descriptive name>",
  "cpt_codes": ["{cpt_code}"],
  "icd_exclusions": ["<ICD codes that make this billing invalid>"],
  "red_flags": ["<clinical conditions that justify the procedure>"],
  "min_conservative_weeks": <integer or null>,
  "requires_prior_imaging": <true or false>,
  "action": "FLAG" or "DENY",
  "plain_english_check": "<One sentence: what to check in the claim>",
  "violation_reason": "<Plain English: why this is a violation if triggered>"
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Convert CMS policy to structured JSON rules. Respond with JSON only."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=600,
        response_format={"type": "json_object"}
    )

    import json
    return json.loads(response.choices[0].message.content)


# ── Summary helpers ───────────────────────────────────────────────────────────

def get_rule_summary() -> list:
    """Return summary of all rules in the library."""
    return [
        {
            "rule_id":       r.rule_id,
            "name":          r.name,
            "cpt_codes":     r.cpt_codes,
            "action":        r.action,
            "source":        r.source_document,
            "source_url":    r.source_url,
            "source_policy": r.source_policy
        }
        for r in POLICY_RULES
    ]
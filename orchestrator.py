from agents.clinical_agent import run_clinical_agent
from agents.fwa_agent import run_fwa_agent
from agents.decision_agent import run_decision_agent

def run_pipeline(case: dict, provider_history: dict = None) -> dict:
    """
    PayGuard AI — 3-Agent FWA Detection Pipeline
    Agent 1: Clinical Reasoning
    Agent 2: FWA Detection
    Agent 3: Decision & Explanation
    """
    clinical_output = run_clinical_agent(case)
    fwa_output = run_fwa_agent(case, clinical_output)
    decision_output = run_decision_agent(case, clinical_output, fwa_output)

    # Parse risk score from Agent 2
    risk_score = "Clean"
    for line in fwa_output.split("\n"):
        if "RISK SCORE:" in line:
            if "High" in line:
                risk_score = "High"
            elif "Medium" in line:
                risk_score = "Medium"
            elif "Low" in line:
                risk_score = "Low"
            else:
                risk_score = "Clean"

    # Parse determination from Agent 3
    if "APPROVE" in decision_output:
        determination = "APPROVE"
    elif "FLAG FOR REVIEW" in decision_output:
        determination = "FLAG FOR REVIEW"
    else:
        determination = "DENY WITH CAUSE"

    # Parse recoverable amount
    import re
    recoverable = 0
    for line in decision_output.split("\n"):
        if "ESTIMATED RECOVERABLE AMOUNT" in line:
            amounts = re.findall(r'\d[\d,]*', line.replace(",", ""))
            if amounts:
                recoverable = int(amounts[0])

    return {
        "case_id": case["case_id"],
        "provider_name": case["provider_name"],
        "provider_id": case.get("provider_id", case["provider_name"]),
        "provider_specialty": case["provider_specialty"],
        "billed_amount": case["billed_amount"],
        "expected_flag": case.get("expected_flag", "UNKNOWN"),
        "clinical_analysis": clinical_output,
        "fwa_analysis": fwa_output,
        "decision": decision_output,
        "determination": determination,
        "risk_score": risk_score,
        "recoverable": recoverable
    }
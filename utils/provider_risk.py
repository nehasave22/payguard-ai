def calculate_provider_risk(provider_claims: list) -> dict:
    """
    Calculates a provider risk profile based on claim history.
    
    Risk levels:
    - CLEAN: 0 FWA flags
    - LOW: 1 flag or <25% flag rate  
    - MEDIUM: 2 flags or 25-50% flag rate
    - HIGH: 3+ flags or >50% flag rate
    - CRITICAL: >75% flag rate with 3+ claims
    """
    if not provider_claims:
        return {
            "risk_level": "UNKNOWN",
            "risk_score": 0,
            "total_claims": 0,
            "flagged_claims": 0,
            "flag_rate": 0,
            "total_billed": 0,
            "total_recoverable": 0,
            "siu_referral": False,
            "pattern_summary": "No claim history available."
        }

    total_claims = len(provider_claims)
    flagged = [c for c in provider_claims if c["determination"] != "APPROVE"]
    flagged_count = len(flagged)
    flag_rate = (flagged_count / total_claims) * 100
    total_billed = sum(c["billed_amount"] for c in provider_claims)
    total_recoverable = sum(c.get("recoverable", 0) for c in provider_claims)

    # Risk scoring algorithm
    risk_score = 0
    risk_score += min(flagged_count * 25, 75)      # Up to 75 pts for flag count
    risk_score += min(flag_rate * 0.25, 25)         # Up to 25 pts for flag rate
    risk_score = min(int(risk_score), 100)

    # Risk level classification
    if risk_score == 0:
        risk_level = "CLEAN"
    elif risk_score < 30:
        risk_level = "LOW"
    elif risk_score < 55:
        risk_level = "MEDIUM"
    elif risk_score < 80:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"

    # SIU referral threshold
    siu_referral = risk_level in ["HIGH", "CRITICAL"]

    # Pattern summary
    deny_count = sum(1 for c in provider_claims if c["determination"] == "DENY WITH CAUSE")
    flag_count = sum(1 for c in provider_claims if c["determination"] == "FLAG FOR REVIEW")
    approve_count = sum(1 for c in provider_claims if c["determination"] == "APPROVE")

    pattern_summary = (
        f"{total_claims} claim(s) reviewed: "
        f"{deny_count} denied, {flag_count} flagged, {approve_count} approved. "
        f"Flag rate: {flag_rate:.0f}%. "
        f"Est. total recoverable: ${total_recoverable:,}."
    )

    if siu_referral:
        pattern_summary += " ⚠️ Pattern consistent with systematic billing abuse."

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "total_claims": total_claims,
        "flagged_claims": flagged_count,
        "flag_rate": round(flag_rate, 1),
        "total_billed": total_billed,
        "total_recoverable": total_recoverable,
        "siu_referral": siu_referral,
        "pattern_summary": pattern_summary
    }


def get_risk_color(risk_level: str) -> str:
    """Returns emoji indicator for risk level."""
    colors = {
        "CLEAN": "🟢",
        "LOW": "🟡",
        "MEDIUM": "🟠",
        "HIGH": "🔴",
        "CRITICAL": "🚨",
        "UNKNOWN": "⚪"
    }
    return colors.get(risk_level, "⚪")
"""
PayGuard AI — Evaluation Harness
=================================
Runs all synthetic claims through the 3-agent pipeline and compares
system output against ground-truth expected_flag labels.

Usage:
    python evaluation.py

Outputs accuracy, per-claim results, and a confusion matrix.
"""

import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Mapping from expected_flag to expected determination ──────────────────────
# UPCODING and SERVICES_NOT_RENDERED should be flagged/denied
# CLEAN should be approved
EXPECTED_DETERMINATION = {
    "UPCODING":              ["DENY WITH CAUSE", "FLAG FOR REVIEW"],
    "SERVICES_NOT_RENDERED": ["DENY WITH CAUSE", "FLAG FOR REVIEW"],
    "CLEAN":                 ["APPROVE"],
}

EXPECTED_RISK = {
    "UPCODING":              ["High", "Medium"],
    "SERVICES_NOT_RENDERED": ["High", "Medium"],
    "CLEAN":                 ["Clean", "Low"],
}


def run_evaluation():
    print("\n" + "="*60)
    print("  PayGuard AI — Evaluation Harness")
    print("  Validating agent pipeline against ground-truth labels")
    print("="*60 + "\n")

    # Load synthetic cases
    with open("data/synthetic_claims.json") as f:
        cases = json.load(f)

    print(f"Loaded {len(cases)} synthetic test cases\n")
    print("-"*60)

    # Import agents
    try:
        from agents.clinical_agent import run_clinical_agent
        from agents.fwa_agent import run_fwa_agent
        from agents.decision_agent import run_decision_agent
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running from the payguard-ai directory")
        sys.exit(1)

    results = []

    for case in cases:
        case_id       = case["case_id"]
        expected_flag = case.get("expected_flag", "UNKNOWN")
        expected_dets = EXPECTED_DETERMINATION.get(expected_flag, [])

        print(f"Running: {case_id}")
        print(f"  Provider:      {case['provider_name']}")
        print(f"  Complaint:     {case['chief_complaint'][:60]}...")
        print(f"  Expected flag: {expected_flag}")

        try:
            # Run pipeline
            clinical = run_clinical_agent(case)
            fwa      = run_fwa_agent(case, clinical)
            decision = run_decision_agent(case, clinical, fwa)

            # Parse determination
            if "APPROVE" in decision:
                determination = "APPROVE"
            elif "FLAG FOR REVIEW" in decision:
                determination = "FLAG FOR REVIEW"
            else:
                determination = "DENY WITH CAUSE"

            # Parse risk score
            risk_score = "Unknown"
            for line in fwa.split("\n"):
                if "RISK SCORE:" in line:
                    for level in ["High", "Medium", "Low", "Clean"]:
                        if level in line:
                            risk_score = level
                            break

            # Parse confidence
            confidence = None
            for line in decision.split("\n"):
                if "CONFIDENCE SCORE:" in line:
                    import re
                    nums = re.findall(r'\d+', line)
                    if nums:
                        confidence = min(max(int(nums[0]), 0), 100)
                    break

            # Evaluate correctness
            det_correct  = determination in expected_dets
            risk_correct = risk_score in EXPECTED_RISK.get(expected_flag, [])
            overall_pass = det_correct

            status = "✓ PASS" if overall_pass else "✗ FAIL"

            print(f"  Determination: {determination} {'✓' if det_correct else '✗'}")
            print(f"  Risk Score:    {risk_score} {'✓' if risk_correct else '✗'}")
            print(f"  Confidence:    {confidence}%")
            print(f"  Result:        {status}")
            print()

            results.append({
                "case_id":       case_id,
                "expected_flag": expected_flag,
                "expected_dets": expected_dets,
                "determination": determination,
                "risk_score":    risk_score,
                "confidence":    confidence,
                "det_correct":   det_correct,
                "risk_correct":  risk_correct,
                "pass":          overall_pass,
            })

        except Exception as e:
            print(f"  ❌ ERROR: {e}\n")
            results.append({
                "case_id":       case_id,
                "expected_flag": expected_flag,
                "determination": "ERROR",
                "pass":          False,
                "error":         str(e),
            })

    # ── Summary ───────────────────────────────────────────────────────────────
    print("="*60)
    print("  EVALUATION SUMMARY")
    print("="*60)

    total  = len(results)
    passed = sum(1 for r in results if r["pass"])
    failed = total - passed
    accuracy = round((passed / total) * 100, 1) if total > 0 else 0

    print(f"\nTotal cases:  {total}")
    print(f"Passed:       {passed}")
    print(f"Failed:       {failed}")
    print(f"Accuracy:     {accuracy}%\n")

    # Per-case table
    print("-"*60)
    print(f"{'Case ID':<20} {'Expected':<25} {'Got':<20} {'Result'}")
    print("-"*60)
    for r in results:
        expected_str = r["expected_flag"]
        got_str      = r.get("determination", "ERROR")
        status       = "✓ PASS" if r["pass"] else "✗ FAIL"
        print(f"{r['case_id']:<20} {expected_str:<25} {got_str:<20} {status}")

    # ── Confusion matrix ──────────────────────────────────────────────────────
    print("\n" + "-"*60)
    print("  CONFUSION MATRIX (Expected Flag vs System Output)")
    print("-"*60)

    categories = ["UPCODING", "SERVICES_NOT_RENDERED", "CLEAN"]
    det_labels = ["APPROVE", "FLAG FOR REVIEW", "DENY WITH CAUSE"]

    matrix = {cat: {det: 0 for det in det_labels} for cat in categories}
    for r in results:
        cat = r.get("expected_flag", "UNKNOWN")
        det = r.get("determination", "ERROR")
        if cat in matrix and det in matrix[cat]:
            matrix[cat][det] += 1

    header = f"{'Expected \\ Got':<25}"
    for det in det_labels:
        header += f"{det[:15]:<16}"
    print(header)
    print("-"*70)
    for cat in categories:
        row = f"{cat:<25}"
        for det in det_labels:
            row += f"{matrix[cat][det]:<16}"
        print(row)

    # ── False positive analysis ───────────────────────────────────────────────
    print("\n" + "-"*60)
    print("  FALSE POSITIVE / FALSE NEGATIVE ANALYSIS")
    print("-"*60)

    fp = [r for r in results if r.get("expected_flag") == "CLEAN"
          and r.get("determination") != "APPROVE"]
    fn = [r for r in results if r.get("expected_flag") in ["UPCODING","SERVICES_NOT_RENDERED"]
          and r.get("determination") == "APPROVE"]

    print(f"False Positives (clean claims flagged):    {len(fp)}")
    print(f"False Negatives (fraud claims approved):   {len(fn)}")

    if fp:
        print("\nFalse Positive details:")
        for r in fp:
            print(f"  {r['case_id']} — got {r['determination']}")
    if fn:
        print("\nFalse Negative details:")
        for r in fn:
            print(f"  {r['case_id']} — got {r['determination']}")

    if not fp and not fn:
        print("\n✓ No false positives or false negatives detected")

    # ── Save results ──────────────────────────────────────────────────────────
    output_file = f"eval_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp":  datetime.now().isoformat(),
            "total":      total,
            "passed":     passed,
            "failed":     failed,
            "accuracy":   accuracy,
            "results":    results
        }, f, indent=2)

    print(f"\n✓ Full results saved to: {output_file}")
    print("\n" + "="*60)
    print(f"  Final Accuracy: {accuracy}% ({passed}/{total} cases correct)")
    print("="*60 + "\n")

    return accuracy


if __name__ == "__main__":
    run_evaluation()
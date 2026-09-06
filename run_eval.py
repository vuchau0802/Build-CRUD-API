"""
Eval runner for the /enrich endpoint.
Run: python run_eval.py
Requires the server running locally on port 8000, with LLM_STUB unset (real calls).
"""
import json
import requests
from pathlib import Path

CASES_PATH = Path(__file__).parent / "evals" / "cases.json"
ENDPOINT = "http://localhost:8000/enrich"


def run_eval():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    total = len(cases)
    correct = 0
    failures = []

    for case in cases:
        try:
            response = requests.post(ENDPOINT, json=case["input"], timeout=35)
        except requests.RequestException as e:
            failures.append({"id": case["id"], "note": case["note"], "reason": f"request failed: {e}"})
            continue

        if response.status_code != 200:
            failures.append({
                "id": case["id"],
                "note": case["note"],
                "reason": f"status {response.status_code}: {response.text}"
            })
            continue

        result = response.json()
        passed = True
        reasons = []

        if case.get("expected_category") is not None:
            if result.get("category") != case["expected_category"]:
                passed = False
                reasons.append(f"expected category '{case['expected_category']}', got '{result.get('category')}'")

        if case.get("expected_flag_contains"):
            if case["expected_flag_contains"] not in result.get("quality_flags", []):
                passed = False
                reasons.append(f"expected flag '{case['expected_flag_contains']}' not present")

        if case.get("expect_low_confidence"):
            if result.get("confidence", 1.0) >= 0.5:
                passed = False
                reasons.append(f"expected confidence < 0.5, got {result.get('confidence')}")

        if case.get("must_be_valid_json"):
            pass  # already implied by status_code == 200 and successful .json()

        if passed:
            correct += 1
        else:
            failures.append({"id": case["id"], "note": case["note"], "reason": "; ".join(reasons), "actual": result})

    print(f"\nEVAL RESULT: {correct}/{total} passed ({round(100 * correct / total)}%)\n")
    if failures:
        print("Failures:")
        for f in failures:
            print(f"  Case {f['id']} ({f['note']}): {f['reason']}")
    else:
        print("All cases passed.")


if __name__ == "__main__":
    run_eval()
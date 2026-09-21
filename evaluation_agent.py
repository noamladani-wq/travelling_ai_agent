"""
Evaluation script for the travel agent pipeline (another_scratch_file.py).

Runs a set of test inputs through process_calendar_request() and checks
whether the output satisfies expected properties: does the gate check
behave correctly, is the destination grounded in the KB when it should be,
does the pipeline avoid inventing unstated details, etc.

Usage:
    python test_travel_agent.py
"""

import sys
import os

# allow importing from the main script in the same folder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from another_scratch_file import process_calendar_request


# Each case: an input + what we expect from the pipeline's behavior.
# expect_pass: whether the gate check should let it through at all.
# expect_kb_used: whether the destination should be found in kb.json
#   (set to None if you don't care / aren't sure without checking logs).
# must_mention: substrings that should appear somewhere in the combined
#   output (case-insensitive) - e.g. the destination name.
# must_not_mention: substrings that should NOT appear - e.g. an airline
#   or detail that was never stated in the input.
test_cases = [
    {
        "name": "Clear single-destination trip, in KB",
        "query": "I am flying next week from Amsterdam to Bangkok for 10 days with KLM.",
        "expect_pass": True,
        "expect_kb_used": True,
        "must_mention": ["bangkok"],
        "must_not_mention": [],
    },
    {
        "name": "Clear trip, destination NOT in KB",
        "query": "I'm traveling to Ulaanbaatar, Mongolia for two weeks starting August 1st.",
        "expect_pass": True,
        "expect_kb_used": False,
        "must_mention": ["ulaanbaatar", "mongolia"],
        "must_not_mention": [],
    },
    {
        "name": "Airline not specified - should say so, not invent one",
        "query": "I'm flying to Lisbon for a long weekend next month.",
        "expect_pass": True,
        "expect_kb_used": True,
        "must_mention": ["lisbon"],
        "must_not_mention": ["klm", "tap", "ryanair", "easyjet"],
    },
    {
        "name": "Non-travel input - should fail the gate check",
        "query": "What's a good recipe for banana bread?",
        "expect_pass": False,
        "expect_kb_used": None,
        "must_mention": [],
        "must_not_mention": [],
    },
    {
        "name": "Vague / low-information input - may or may not pass",
        "query": "thinking about maybe going somewhere sometime",
        "expect_pass": False,
        "expect_kb_used": None,
        "must_mention": [],
        "must_not_mention": [],
    },
    {
        "name": "Multi-destination trip (known limitation - single city extraction)",
        "query": "I'm flying to Central Asia, visiting both Bishkek, Kyrgyzstan and Almaty, Kazakhstan over three weeks.",
        "expect_pass": True,
        "expect_kb_used": True,
        "must_mention": [],  # intentionally loose - this case documents a limitation, not a hard pass/fail
        "must_not_mention": [],
    },
    {
        "name": "Short trip, in KB, solo traveler safety framing",
        "query": "I'm a solo female traveler flying to Tokyo for 5 days in October.",
        "expect_pass": True,
        "expect_kb_used": True,
        "must_mention": ["tokyo"],
        "must_not_mention": [],
    },
    {
        "name": "Long trip (month+), should still produce an itinerary",
        "query": "I'm flying to Istanbul for six weeks starting in September, no specific plans yet.",
        "expect_pass": True,
        "expect_kb_used": True,
        "must_mention": ["istanbul"],
        "must_not_mention": [],
    },
]


def run_case(case: dict) -> dict:
    """Run a single test case and score it against expectations."""
    result_row = {"name": case["name"], "query": case["query"]}

    try:
        result = process_calendar_request(case["query"])
    except Exception as exc:
        result_row["error"] = str(exc)
        result_row["passed_gate_check"] = False
        result_row["checks"] = {}
        return result_row

    passed_gate = result is not None
    result_row["passed_gate_check"] = passed_gate

    checks = {}
    checks["gate_check_as_expected"] = (passed_gate == case["expect_pass"])

    if passed_gate:
        combined_text = " ".join([
            result.flight_info,
            result.weather_info,
            result.safety_info,
            " ".join(result.itinerary),
        ]).lower()

        for term in case["must_mention"]:
            checks[f"mentions '{term}'"] = term.lower() in combined_text

        for term in case["must_not_mention"]:
            checks[f"avoids '{term}'"] = term.lower() not in combined_text

        checks["itinerary_non_empty"] = len(result.itinerary) > 0
        checks["flight_confidence_in_range"] = 0.0 <= result.flight_confidence <= 1.0

        result_row["flight_info"] = result.flight_info
        result_row["weather_info"] = result.weather_info
        result_row["safety_info"] = result.safety_info
        result_row["itinerary_days"] = len(result.itinerary)

    result_row["checks"] = checks
    return result_row


def run_evaluation():
    all_results = []

    for i, case in enumerate(test_cases):
        print(f"\n--- Test {i + 1}/{len(test_cases)}: {case['name']} ---")
        print(f"Query: {case['query']}")

        row = run_case(case)

        if "error" in row:
            print(f"CRASHED: {row['error']}")
        else:
            passed = sum(1 for v in row["checks"].values() if v)
            total = len(row["checks"])
            print(f"Gate check passed: {row['passed_gate_check']}")
            print(f"Checks passed: {passed}/{total} -> {row['checks']}")

        all_results.append(row)

    # summary
    print("\n\n=== SUMMARY ===")
    total_checks = 0
    total_passed = 0
    crashes = 0

    for row in all_results:
        if "error" in row:
            crashes += 1
            continue
        for passed in row["checks"].values():
            total_checks += 1
            if passed:
                total_passed += 1

    print(f"Cases run: {len(all_results)}")
    print(f"Cases that crashed: {crashes}")
    print(f"Total checks passed: {total_passed}/{total_checks}")

    return all_results


if __name__ == "__main__":
    run_evaluation()
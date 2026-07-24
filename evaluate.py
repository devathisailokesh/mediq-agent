"""
Evaluation script for MediQ Agent.

Runs each scenario from tests/scenarios.json directly against the
MediQAgent pipeline — no FastAPI server required.

Scores each answer on:
  - Keyword coverage  : expected medical terms present in the answer
  - Citation presence : at least one PubMed citation returned
  - Answer length     : answer is at least 100 characters

Usage:
    python evaluate.py
    python evaluate.py --scenarios tests/scenarios.json
"""

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from logs.logger import get_logger
from src.agents.agent import MediQAgent

logger = get_logger(__name__)

PASS_THRESHOLD = 0.6

# Initialised once — avoids creating a new Groq client per scenario
_agent = MediQAgent()


def load_scenarios(path: str) -> list:
    """
    Load test scenarios from a JSON file.

    Args:
        path: Path to the scenarios JSON file.

    Returns:
        list: List of scenario dicts.

    Raises:
        RuntimeError: If the file cannot be read or parsed.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, PermissionError) as exc:
        logger.error("load_scenarios failed | path=%s | error=%s", path, exc, exc_info=True)
        raise RuntimeError(f"Cannot open scenarios file: {exc}") from exc
    except json.JSONDecodeError as exc:
        logger.error("load_scenarios JSON error | path=%s | error=%s", path, exc, exc_info=True)
        raise RuntimeError(f"Invalid JSON in scenarios file: {exc}") from exc


def run_scenario(scenario: dict) -> dict:
    """
    Run a single scenario through the agent pipeline and return scored results.

    Args:
        scenario: Scenario dict from scenarios.json.

    Returns:
        dict: Result with score, pass/fail flag, and per-metric breakdown.
    """
    session_id = str(uuid.uuid4())
    question = scenario["question"]
    expected_keywords = [kw.lower() for kw in scenario.get("expected_keywords", [])]
    expects_citations = scenario.get("expected_citations", True)

    logger.info("Running scenario '%s'", scenario["id"])

    try:
        start = time.time()
        result = _agent.run(query=question, session_id=session_id)
        duration = round(time.time() - start, 2)

        answer = result.get("answer", "").lower()
        citations = result.get("citations", [])

        # Keyword coverage score
        matched = [kw for kw in expected_keywords if kw in answer]
        keyword_score = len(matched) / len(expected_keywords) if expected_keywords else 1.0

        # Citation presence score
        citation_score = 1.0 if (not expects_citations or len(citations) > 0) else 0.0

        # Answer length score (minimum 100 chars)
        length_score = 1.0 if len(answer) >= 100 else 0.0

        total_score = round((keyword_score + citation_score + length_score) / 3, 2)
        passed = total_score >= PASS_THRESHOLD

        logger.info(
            "Scenario '%s' %s | score=%.2f | keywords=%d/%d | citations=%d",
            scenario["id"],
            "PASS" if passed else "FAIL",
            total_score,
            len(matched),
            len(expected_keywords),
            len(citations),
        )

        return {
            "id": scenario["id"],
            "question": question,
            "domain": scenario.get("domain", ""),
            "passed": passed,
            "score": total_score,
            "keyword_score": round(keyword_score, 2),
            "citation_score": citation_score,
            "length_score": length_score,
            "keywords_matched": matched,
            "keywords_missed": [kw for kw in expected_keywords if kw not in answer],
            "citations_found": len(citations),
            "answer_length": len(answer),
            "duration_seconds": duration,
            "answer_preview": result.get("answer", "")[:200],
        }

    except Exception as exc:
        logger.error("Scenario '%s' failed | error=%s", scenario.get("id"), exc, exc_info=True)
        return {
            "id": scenario.get("id", "unknown"),
            "question": question,
            "passed": False,
            "score": 0.0,
            "error": str(exc),
        }


def print_report(results: list) -> None:
    """
    Print a formatted evaluation report to stdout.

    Args:
        results: List of scenario result dicts.
    """
    passed = sum(1 for r in results if r.get("passed"))
    total = len(results)
    avg_score = round(sum(r.get("score", 0) for r in results) / total, 2) if total else 0

    print("\n" + "=" * 70)
    print("  MEDIQ AGENT — EVALUATION REPORT")
    print(f"  Scenarios: {total} | Passed: {passed} | Failed: {total - passed}")
    print(f"  Average Score: {avg_score} | Pass Threshold: {PASS_THRESHOLD}")
    print("=" * 70)

    for r in results:
        status = "PASS" if r.get("passed") else "FAIL"
        print(f"\n[{status}] {r['id']} | score={r.get('score', 0):.2f} | domain={r.get('domain', '')}")
        print(f"  Question : {r['question'][:80]}")
        if r.get("error"):
            print(f"  Error    : {r['error']}")
        else:
            print(f"  Keywords : matched={r.get('keywords_matched', [])} | missed={r.get('keywords_missed', [])}")
            print(f"  Citations: {r.get('citations_found', 0)} | Length: {r.get('answer_length', 0)} chars")
            print(f"  Duration : {r.get('duration_seconds', 0)}s")
            print(f"  Preview  : {r.get('answer_preview', '')[:150]}...")

    print("\n" + "=" * 70)
    print(f"  RESULT: {'ALL PASSED' if passed == total else f'{passed}/{total} PASSED'}")
    print("=" * 70 + "\n")


def save_output(results: list, output_path: Path) -> None:
    """
    Save evaluation results to a JSON file.

    Args:
        results: List of scenario result dicts.
        output_path: Destination file path.
    """
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        logger.info("Results saved to %s", output_path)
        print(f"[INFO] Results saved to: {output_path}")
    except (OSError, IOError, TypeError) as exc:
        logger.warning("save_output failed | path=%s | error=%s", output_path, exc, exc_info=True)


def main() -> None:
    """Entry point — parse args, run all scenarios, print report, save results."""
    try:
        parser = argparse.ArgumentParser(description="Evaluate MediQ Agent")
        parser.add_argument(
            "--scenarios",
            default="tests/scenarios.json",
            help="Path to scenarios JSON file (default: tests/scenarios.json)",
        )
        args = parser.parse_args()

        scenarios = load_scenarios(args.scenarios)
        logger.info("Loaded %d scenarios from %s", len(scenarios), args.scenarios)

        results = [run_scenario(s) for s in scenarios]

        print_report(results)
        save_output(results, Path("logs") / "evaluation_results.json")

        passed = sum(1 for r in results if r.get("passed"))
        sys.exit(0 if passed == len(results) else 1)

    except RuntimeError as exc:
        print(f"\n[ERROR] {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Evaluation interrupted.")
        sys.exit(0)
    except Exception as exc:
        logger.error("main failed | error=%s", exc, exc_info=True)
        print(f"\n[ERROR] Unexpected error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

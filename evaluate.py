"""
Evaluation script for MediQ Agent.

Runs each scenario from tests/scenarios.json against the live agent pipeline
and scores outputs on keyword coverage, citation presence, and answer length.

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

import httpx

from logs.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "http://localhost:8000"
PASS_THRESHOLD = 0.6


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
        logger.error("load_scenarios could not open file | path=%s | error=%s", path, exc, exc_info=True)
        raise RuntimeError(f"load_scenarios failed — file not accessible: {exc}") from exc
    except json.JSONDecodeError as exc:
        logger.error("load_scenarios JSON parse error | path=%s | error=%s", path, exc, exc_info=True)
        raise RuntimeError(f"load_scenarios failed — invalid JSON: {exc}") from exc
    except Exception as exc:
        logger.error("load_scenarios failed | path=%s | error=%s", path, exc, exc_info=True)
        raise RuntimeError(f"load_scenarios failed: {exc}") from exc


def run_scenario(scenario: dict) -> dict:
    """
    Run a single scenario against the live API and return scored results.

    Args:
        scenario: Scenario dict from scenarios.json.

    Returns:
        dict: Result containing score, pass/fail, and details.
    """
    try:
        session_id = str(uuid.uuid4())
        question = scenario["question"]
        expected_keywords = [kw.lower() for kw in scenario.get("expected_keywords", [])]
        expects_citations = scenario.get("expected_citations", True)

        logger.info("Running scenario '%s'", scenario["id"])

        try:
            start = time.time()
            response = httpx.post(
                f"{BASE_URL}/query",
                json={"question": question, "session_id": session_id},
                timeout=120.0,
            )
            duration = round(time.time() - start, 2)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error("Scenario '%s' request failed: %s", scenario["id"], exc, exc_info=True)
            return {
                "id": scenario["id"],
                "question": question,
                "passed": False,
                "score": 0.0,
                "error": str(exc),
            }

        answer = data.get("answer", "").lower()
        citations = data.get("citations", [])

        # Keyword coverage score
        matched = [kw for kw in expected_keywords if kw in answer]
        keyword_score = len(matched) / len(expected_keywords) if expected_keywords else 1.0

        # Citation check
        citation_score = 1.0 if (not expects_citations or len(citations) > 0) else 0.0

        # Answer length check (at least 100 chars)
        length_score = 1.0 if len(answer) >= 100 else 0.0

        total_score = round((keyword_score + citation_score + length_score) / 3, 2)
        passed = total_score >= PASS_THRESHOLD

        result = {
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
            "answer_preview": data.get("answer", "")[:200],
        }

        status = "PASS" if passed else "FAIL"
        logger.info(
            "Scenario '%s' %s | score=%.2f | keywords=%d/%d | citations=%d",
            scenario["id"],
            status,
            total_score,
            len(matched),
            len(expected_keywords),
            len(citations),
        )
        return result
    except Exception as exc:
        logger.error(
            "run_scenario failed | scenario_id=%s | error=%s",
            scenario.get("id", "unknown"), exc, exc_info=True,
        )
        return {
            "id": scenario.get("id", "unknown"),
            "question": scenario.get("question", ""),
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
    try:
        passed = sum(1 for r in results if r.get("passed"))
        total = len(results)
        avg_score = round(sum(r.get("score", 0) for r in results) / total, 2) if total else 0

        print("\n" + "=" * 70)
        print("  MEDIQ AGENT EVALUATION REPORT")
        print(f"  Scenarios: {total} | Passed: {passed} | Failed: {total - passed}")
        print(f"  Average Score: {avg_score} | Pass Threshold: {PASS_THRESHOLD}")
        print("=" * 70)

        for r in results:
            status = "✓ PASS" if r.get("passed") else "✗ FAIL"
            print(f"\n[{status}] {r['id']} | score={r.get('score', 0):.2f} | domain={r.get('domain', '')}")
            print(f"  Question: {r['question'][:80]}")
            if r.get("error"):
                print(f"  Error: {r['error']}")
            else:
                print(f"  Keywords matched: {r.get('keywords_matched', [])} | missed: {r.get('keywords_missed', [])}")
                print(f"  Citations: {r.get('citations_found', 0)} | Answer length: {r.get('answer_length', 0)} chars")
                print(f"  Duration: {r.get('duration_seconds', 0)}s")
                print(f"  Preview: {r.get('answer_preview', '')[:150]}...")

        print("\n" + "=" * 70)
        print(f"  RESULT: {'ALL PASSED' if passed == total else f'{passed}/{total} PASSED'}")
        print("=" * 70 + "\n")
    except Exception as exc:
        logger.warning("print_report failed | error=%s", exc, exc_info=True)


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
    except (OSError, IOError, TypeError) as exc:
        logger.warning(
            "save_output failed | path=%s | error=%s", output_path, exc, exc_info=True,
        )


def main() -> None:
    """Entry point — parse args, run scenarios, print report."""
    try:
        parser = argparse.ArgumentParser(description="Evaluate MediQ Agent")
        parser.add_argument(
            "--scenarios",
            default="tests/scenarios.json",
            help="Path to scenarios JSON file",
        )
        parser.add_argument(
            "--base-url",
            default=BASE_URL,
            help="FastAPI base URL (default: http://localhost:8000)",
        )
        args = parser.parse_args()

        scenarios = load_scenarios(args.scenarios)
        logger.info("Loaded %d scenarios from %s", len(scenarios), args.scenarios)

        results = [run_scenario(s) for s in scenarios]

        print_report(results)

        output_path = Path("logs") / "evaluation_results.json"
        save_output(results, output_path)

        passed = sum(1 for r in results if r.get("passed"))
        sys.exit(0 if passed == len(results) else 1)
    except RuntimeError as exc:
        logger.error("Evaluation aborted | error=%s", exc, exc_info=True)
        print(f"\n[ERROR] {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Evaluation interrupted by user.")
        sys.exit(0)
    except Exception as exc:
        logger.error("main failed | error=%s", exc, exc_info=True)
        print(f"\n[ERROR] Unexpected error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

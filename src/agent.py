"""
MediQ Agent — CLI entry point.

Thin wrapper that parses CLI arguments and delegates to MediQAgent
in src/agents/agent.py.

Usage:
    python src/agent.py --domain healthcare --query "What are the latest treatments for Type 2 diabetes?"
    python src/agent.py --query "Side effects of metformin in elderly?" --max-papers 3
    python src/agent.py --query "Hypertension guidelines" --output results.json
"""

import argparse
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from logs.logger import get_logger
from src.agents.agent import MediQAgent

logger = get_logger(__name__)

SUPPORTED_DOMAINS = ["healthcare", "medical", "clinical"]


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="MediQ Agent — Agentic medical Q&A using PubMed RAG and Groq LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/agent.py --domain healthcare --query "What are the latest treatments for Type 2 diabetes?"
  python src/agent.py --query "Side effects of metformin in elderly?" --max-papers 3 --session my-session
  python src/agent.py --query "Hypertension management guidelines" --output results.json
        """,
    )
    parser.add_argument(
        "--domain",
        type=str,
        default="healthcare",
        choices=SUPPORTED_DOMAINS,
        help="Agent domain (default: healthcare)",
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Medical question to answer",
    )
    parser.add_argument(
        "--max-papers",
        type=int,
        default=None,
        metavar="N",
        help="Max PubMed papers to retrieve (default: from .env, usually 5)",
    )
    parser.add_argument(
        "--session",
        type=str,
        default=None,
        help="Session ID for conversation memory (auto-generated if omitted)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        metavar="FILE",
        help="Save full JSON result to this file (optional)",
    )
    return parser.parse_args()


def validate_query(query: str) -> None:
    """
    Validate the user query before sending it to the pipeline.

    Args:
        query: Raw query string from CLI.

    Raises:
        SystemExit: If the query fails validation.
    """
    try:
        if len(query.strip()) < 5:
            print("[ERROR] Query is too short. Please provide a meaningful medical question.")
            sys.exit(1)
        if len(query) > 1000:
            print("[ERROR] Query exceeds 1000 characters. Please shorten your question.")
            sys.exit(1)
    except SystemExit:
        raise
    except Exception as exc:
        logger.error("validate_query failed | error=%s", exc, exc_info=True)
        raise RuntimeError(f"validate_query failed: {exc}") from exc


def print_result(result: dict) -> None:
    """
    Print the agent result in a readable format to stdout.

    Args:
        result: Result dict returned by MediQAgent.run().
    """
    try:
        print("\n" + "=" * 70)
        print("  MEDIQ AGENT — ANSWER")
        print("=" * 70)
        print(f"\nQuestion: {result['question']}\n")
        print(result["answer"])

        if result["citations"]:
            print("\n" + "-" * 70)
            print("  CITATIONS")
            print("-" * 70)
            for c in result["citations"]:
                authors = ", ".join(c["authors"]) + (" et al." if len(c["authors"]) >= 3 else "")
                print(f"\n  [PMID: {c['pubmed_id']}]")
                print(f"  Title  : {c['title']}")
                print(f"  Authors: {authors}")
                print(f"  Journal: {c['journal']} ({c['pub_date']})")
                print(f"  URL    : {c['url']}")

        trace = result["trace"]
        print("\n" + "-" * 70)
        print(f"  Session : {result['session_id']}")
        print(f"  Papers  : {trace['papers_retrieved']}")
        print(f"  Duration: {trace['total_duration_seconds']}s")
        print("=" * 70 + "\n")
    except Exception as exc:
        logger.warning("print_result failed | error=%s", exc, exc_info=True)


def save_output(result: dict, path: str) -> None:
    """
    Save the full result dictionary as JSON to a file.

    Args:
        result: Result dict returned by MediQAgent.run().
        path: Destination file path.
    """
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"[INFO] Full result saved to: {path}")
    except (OSError, IOError, TypeError) as exc:
        logger.warning("save_output failed | path=%s | error=%s", path, exc, exc_info=True)


def main() -> None:
    """Entry point — parse args, validate, delegate to MediQAgent, print result."""
    try:
        args = parse_args()
        validate_query(args.query)

        session_id = args.session or str(uuid.uuid4())

        print(f"\nMediQ Agent | domain={args.domain} | session={session_id}")
        print(f"Query: {args.query}")
        print("\n[1/3] Planning search strategy...")

        try:
            agent = MediQAgent()
            result = agent.run(
                query=args.query,
                session_id=session_id,
                max_papers=args.max_papers,
            )
            print_result(result)

            if args.output:
                save_output(result, args.output)

        except KeyboardInterrupt:
            print("\n[INFO] Interrupted by user.")
            sys.exit(0)
        except Exception as exc:
            logger.error("Agent failed: %s", exc, exc_info=True)
            print(f"\n[ERROR] {exc}")
            sys.exit(1)
    except SystemExit:
        raise
    except Exception as exc:
        logger.error("main failed | error=%s", exc, exc_info=True)
        print(f"\n[ERROR] Unexpected error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

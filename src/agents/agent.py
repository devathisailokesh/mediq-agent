"""
MediQ Agent pipeline orchestrator.

Wires together Planner → Researcher → Summarizer into a single run() call
that can be invoked from the CLI (src/agent.py) or the FastAPI layer.
"""

import time
import uuid
from typing import Optional

# Medical domain keywords used by the content guardrail
_MEDICAL_KEYWORDS = {
    "disease", "disorder", "syndrome", "symptom", "treatment", "therapy",
    "drug", "medication", "dose", "dosage", "clinical", "patient", "diagnosis",
    "cancer", "tumor", "infection", "vaccine", "surgery", "hospital", "medical",
    "health", "pain", "blood", "heart", "lung", "kidney", "liver", "brain",
    "diabetes", "hypertension", "antibiotic", "virus", "bacteria", "gene",
    "protein", "enzyme", "trial", "study", "evidence", "risk", "prevention",
}

from logs.logger import get_logger
from src.agents.planner import PlannerAgent
from src.agents.researcher import ResearcherAgent
from src.agents.summarizer import SummarizerAgent
from src.memory.store import MemoryStore
from src.schemas import AgentTrace

logger = get_logger(__name__)


class MediQAgent:
    """
    Top-level orchestrator for the MediQ multi-agent pipeline.

    Instantiate once and call run() for each query.
    All three agents and the memory store are initialised on construction.
    """

    def __init__(self) -> None:
        """
        Initialise all agents and the memory store.

        Raises:
            RuntimeError: If any agent or store fails to initialise.
        """
        try:
            self._planner = PlannerAgent()
            self._researcher = ResearcherAgent()
            self._summarizer = SummarizerAgent()
            self._store = MemoryStore()
            logger.info("MediQAgent ready")
        except Exception as exc:
            logger.error("MediQAgent failed to initialise: %s", exc, exc_info=True)
            raise RuntimeError(f"MediQAgent initialisation failed: {exc}") from exc

    def run(
        self,
        query: str,
        session_id: Optional[str] = None,
        max_papers: Optional[int] = None,
    ) -> dict:
        """
        Execute the full agent pipeline for a medical question.

        Steps:
            1. PlannerAgent    — builds PubMed search plan (chain-of-thought)
            2. ResearcherAgent — fetches papers and extracts findings (RAG)
            3. SummarizerAgent — synthesizes final cited answer (self-critique)

        Args:
            query: User's medical question.
            session_id: Session ID for memory continuity. Auto-generated if None.
            max_papers: Override max papers per PubMed query.

        Returns:
            dict: {session_id, question, answer, citations, trace}

        Raises:
            RuntimeError: If any pipeline step fails after all retries.
        """
        session_id = session_id or str(uuid.uuid4())
        start_time = time.time()
        steps = []

        logger.info("MediQAgent.run | session=%s | query='%s'", session_id, query[:80])

        # Content guardrail — reject clearly non-medical questions early
        if not self._is_medical_query(query):
            logger.warning("Content guardrail triggered | query='%s'", query[:80])
            return {
                "session_id": session_id,
                "question": query,
                "answer": (
                    "MediQ is a medical research assistant and can only answer "
                    "healthcare-related questions. Please ask about a disease, "
                    "treatment, medication, or clinical topic."
                ),
                "citations": [],
                "trace": {
                    "session_id": session_id,
                    "query": query,
                    "steps": [],
                    "papers_retrieved": 0,
                    "total_duration_seconds": 0.0,
                },
            }

        try:
            history = self._store.format_history_for_prompt(session_id)

            # Step 1 — Plan
            logger.info("Step 1: Planning")
            try:
                plan, planner_step = self._planner.plan(query, history=history)
                steps.append(planner_step)
            except Exception as exc:
                logger.error("Planner step failed: %s", exc, exc_info=True)
                raise RuntimeError(f"Planning failed: {exc}") from exc

            # Step 2 — Research
            logger.info("Step 2: Researching")
            try:
                research_summary, papers, researcher_step = self._researcher.research(
                    query, plan, max_papers=max_papers
                )
                steps.append(researcher_step)
            except Exception as exc:
                logger.error("Researcher step failed: %s", exc, exc_info=True)
                raise RuntimeError(f"Research failed: {exc}") from exc

            # Step 3 — Summarize
            logger.info("Step 3: Summarizing")
            try:
                answer, summarizer_step = self._summarizer.summarize(
                    query, research_summary, papers, history=history
                )
                steps.append(summarizer_step)
            except Exception as exc:
                logger.error("Summarizer step failed: %s", exc, exc_info=True)
                raise RuntimeError(f"Summarization failed: {exc}") from exc

            # Persist to memory — failure here should not break the response
            try:
                self._store.save_turn(session_id, query, answer)
            except Exception as exc:
                logger.warning("Memory save failed (non-fatal): %s", exc)

            trace = AgentTrace(
                session_id=session_id,
                query=query,
                steps=steps,
                papers_retrieved=len(papers),
                total_duration_seconds=round(time.time() - start_time, 2),
            )

            citations = [
                {
                    "pubmed_id": p.pubmed_id,
                    "title": p.title,
                    "authors": p.authors[:3],
                    "journal": p.journal,
                    "pub_date": p.pub_date,
                    "url": p.url,
                }
                for p in papers
            ]

            logger.info(
                "MediQAgent.run complete | papers=%d | duration=%.2fs",
                len(papers),
                trace.total_duration_seconds,
            )

            return {
                "session_id": session_id,
                "question": query,
                "answer": answer,
                "citations": citations,
                "trace": trace.model_dump(mode="json"),
            }

        except RuntimeError:
            raise
        except Exception as exc:
            logger.error("Unexpected pipeline error: %s", exc, exc_info=True)
            raise RuntimeError(f"Pipeline error: {exc}") from exc

    @staticmethod
    def _is_medical_query(query: str) -> bool:
        """
        Content guardrail — returns False for clearly non-medical questions.

        Uses keyword matching against a curated medical vocabulary.
        Short-circuits to True when any medical term is found.

        Args:
            query: Raw user question.

        Returns:
            bool: True if the query appears medical, False otherwise.
        """
        try:
            words = set(query.lower().split())
            return bool(words & _MEDICAL_KEYWORDS)
        except Exception:
            return True  

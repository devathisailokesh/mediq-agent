"""
Researcher Agent — fetches PubMed papers and extracts key findings.

Runs multiple search queries from the Planner's plan, deduplicates results,
and asks the LLM to extract relevant findings from the retrieved abstracts.
"""

from typing import List, Tuple

from groq import Groq

from logs.logger import get_logger
from src.config.settings import settings
from src.schemas import AgentStep, PubMedPaper, SearchPlan
from src.prompts.templates import RESEARCHER_SYSTEM_PROMPT, RESEARCHER_USER_TEMPLATE
from src.tools.pubmed import PubMedClient
from src.utils.retry import retry_with_backoff

logger = get_logger(__name__)


class ResearcherAgent:
    """
    Retrieves PubMed papers based on the search plan and summarises findings.

    Implements RAG: retrieved abstracts are injected into the LLM context
    so the model reasons over real research rather than its training data.
    """

    def __init__(self) -> None:
        """Initialise Groq client and PubMed tool."""
        self._client = Groq(api_key=settings.groq_api_key)
        self._model = settings.groq_model
        self._pubmed = PubMedClient()
        logger.info("ResearcherAgent initialised | model=%s", self._model)

    def research(
        self, question: str, plan: SearchPlan, max_papers: int | None = None
    ) -> Tuple[str, List[PubMedPaper], AgentStep]:
        """
        Execute the search plan, retrieve papers, and extract findings.

        Args:
            question: Original user question.
            plan: SearchPlan produced by the PlannerAgent.
            max_papers: Override for max papers per query.

        Returns:
            Tuple containing:
                - str: Research summary from the LLM.
                - List[PubMedPaper]: Deduplicated papers retrieved.
                - AgentStep: Trace step for observability.

        Raises:
            RuntimeError: If the research pipeline fails unexpectedly.
        """
        try:
            logger.info("[RESEARCHER INPUT] Question: %s | Queries: %d | Max Papers: %s", question[:60], len(plan.search_queries), max_papers or "default")

            papers = self._fetch_papers(plan, max_papers)

            if not papers:
                logger.warning("No papers retrieved — returning empty-handed response")
                summary = "No relevant PubMed papers were found for this query."
                step = AgentStep(
                    agent="researcher",
                    action="fetch_and_summarise",
                    input=str(plan.search_queries),
                    output=summary,
                )
                return summary, [], step

            summary = self._summarise_papers(question, papers)
            step = AgentStep(
                agent="researcher",
                action="fetch_and_summarise",
                input=str(plan.search_queries),
                output=f"Retrieved {len(papers)} papers. Summary length: {len(summary)} chars.",
            )
            return summary, papers, step
        except RuntimeError:
            raise
        except Exception as exc:
            logger.error(
                "ResearcherAgent.research failed | question='%s' | error=%s",
                question[:80], exc, exc_info=True,
            )
            raise RuntimeError(f"ResearcherAgent.research failed: {exc}") from exc

    def _fetch_papers(
        self, plan: SearchPlan, max_papers: int | None
    ) -> List[PubMedPaper]:
        """
        Run all search queries and return a deduplicated list of papers.

        Args:
            plan: SearchPlan with queries to run.
            max_papers: Papers per query limit.

        Returns:
            List[PubMedPaper]: Unique papers across all queries.

        Raises:
            RuntimeError: If paper fetching fails unexpectedly.
        """
        try:
            seen_ids: set = set()
            all_papers: List[PubMedPaper] = []

            for query in plan.search_queries:
                try:
                    papers = self._pubmed.search_and_fetch(query, max_papers)
                    for paper in papers:
                        if paper.pubmed_id not in seen_ids:
                            seen_ids.add(paper.pubmed_id)
                            all_papers.append(paper)
                except Exception as exc:
                    logger.error(
                        "PubMed query failed | query='%s' | error=%s", query, exc, exc_info=True,
                    )

            logger.info("[RESEARCHER OUTPUT] Papers Fetched: %d", len(all_papers))
            for paper in all_papers:
                logger.info("  PMID:%s | %s", paper.pubmed_id, paper.title[:70])
            return all_papers
        except Exception as exc:
            logger.error(
                "ResearcherAgent._fetch_papers failed | error=%s", exc, exc_info=True,
            )
            raise RuntimeError(f"ResearcherAgent._fetch_papers failed: {exc}") from exc

    def _summarise_papers(self, question: str, papers: List[PubMedPaper]) -> str:
        """
        Ask the LLM to extract key findings from the retrieved abstracts (RAG step).

        Args:
            question: User's question.
            papers: Retrieved PubMed papers with abstracts.

        Returns:
            str: LLM-generated research summary grounded in the abstracts.

        Raises:
            RuntimeError: If all LLM retries are exhausted.
        """
        try:
            abstracts_block = "\n\n".join(
                f"[PMID: {p.pubmed_id}] {p.title}\nAuthors: {', '.join(p.authors[:3])}\n"
                f"Journal: {p.journal} ({p.pub_date})\nAbstract: {p.abstract}"
                for p in papers
            )
            # Token-limit guard: truncate abstracts block to avoid exceeding context window
            limit = settings.max_context_chars
            if len(abstracts_block) > limit:
                abstracts_block = abstracts_block[:limit] + "\n\n[... truncated to fit context limit ...]"
                logger.warning(
                    "Abstracts block truncated to %d chars to stay within context limit", limit
                )
            user_message = RESEARCHER_USER_TEMPLATE.format(
                question=question, abstracts=abstracts_block
            )

            def _call() -> str:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": RESEARCHER_SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=settings.temperature,
                    max_tokens=settings.max_tokens,
                    timeout=settings.groq_timeout,
                )
                return response.choices[0].message.content

            summary = retry_with_backoff(
                fn=_call,
                max_retries=settings.max_retries,
                base_delay=settings.retry_delay,
                label="ResearcherAgent/Groq",
            )
            logger.info("[RESEARCHER SUMMARY] Length: %d chars | Preview: %s", len(summary), summary[:100])
            return summary
        except RuntimeError:
            raise
        except Exception as exc:
            logger.error(
                "ResearcherAgent._summarise_papers failed | error=%s", exc, exc_info=True,
            )
            raise RuntimeError(f"ResearcherAgent._summarise_papers failed: {exc}") from exc

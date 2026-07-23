"""
Summarizer Agent — synthesizes research findings into a final user-facing answer.

Implements self-critique: the system prompt instructs the model to verify
its own output before returning, ensuring all claims are grounded in the papers.
"""

from typing import List

from groq import Groq

from logs.logger import get_logger
from src.config.settings import settings
from src.schemas import AgentStep, PubMedPaper
from src.prompts.templates import SUMMARIZER_SYSTEM_PROMPT, SUMMARIZER_USER_TEMPLATE
from src.utils.retry import retry_with_backoff

logger = get_logger(__name__)


class SummarizerAgent:
    """
    Produces the final, user-facing answer from research findings.

    Uses self-reflection (built into the system prompt) to verify the answer
    before returning it, reducing hallucination and improving answer quality.
    """

    def __init__(self) -> None:
        """Initialise Groq client with settings from config."""
        self._client = Groq(api_key=settings.groq_api_key)
        self._model = settings.groq_model
        logger.info("SummarizerAgent initialised | model=%s", self._model)

    def summarize(
        self,
        question: str,
        research_summary: str,
        papers: List[PubMedPaper],
        history: str = "",
    ) -> tuple[str, AgentStep]:
        """
        Generate the final answer by synthesizing research findings.

        Args:
            question: Original user question.
            research_summary: Key findings extracted by the ResearcherAgent.
            papers: Retrieved PubMed papers (used for citation metadata).
            history: Formatted prior conversation for context.

        Returns:
            tuple[str, AgentStep]: Final answer text and trace step.

        Raises:
            RuntimeError: If all LLM API retries are exhausted.
        """
        try:
            logger.info("SummarizerAgent.summarize | question='%s'", question[:80])

            paper_metadata = self._format_paper_metadata(papers)
            user_message = SUMMARIZER_USER_TEMPLATE.format(
                question=question,
                research_summary=research_summary,
                paper_metadata=paper_metadata,
                history=history,
            )

            answer = self._call_llm_with_retry(user_message)

            step = AgentStep(
                agent="summarizer",
                action="synthesize_answer",
                input=question,
                output=answer[:300] + "..." if len(answer) > 300 else answer,
            )
            logger.info("SummarizerAgent produced answer | length=%d chars", len(answer))
            return answer, step
        except RuntimeError:
            raise
        except Exception as exc:
            logger.error(
                "SummarizerAgent.summarize failed | question='%s' | error=%s",
                question[:80], exc, exc_info=True,
            )
            raise RuntimeError(f"SummarizerAgent.summarize failed: {exc}") from exc

    def _call_llm_with_retry(self, user_message: str) -> str:
        """
        Call the Groq LLM with exponential backoff retry on transient failures.

        Args:
            user_message: Formatted prompt to send.

        Returns:
            str: Raw LLM answer text.

        Raises:
            RuntimeError: If all retries are exhausted.
        """
        def _call() -> str:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SUMMARIZER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
                timeout=settings.groq_timeout,
            )
            return response.choices[0].message.content

        return retry_with_backoff(
            fn=_call,
            max_retries=settings.max_retries,
            base_delay=settings.retry_delay,
            label="SummarizerAgent/Groq",
        )

    @staticmethod
    def _format_paper_metadata(papers: List[PubMedPaper]) -> str:
        """
        Format paper metadata into a concise reference list for the prompt.

        Args:
            papers: List of retrieved PubMed papers.

        Returns:
            str: Formatted reference block.
        """
        try:
            if not papers:
                return "No papers available."

            lines = []
            for p in papers:
                authors_str = ", ".join(p.authors[:3]) + (" et al." if len(p.authors) > 3 else "")
                lines.append(
                    f"- [PMID: {p.pubmed_id}] {p.title} | {authors_str} | {p.journal} ({p.pub_date}) | {p.url}"
                )
            return "\n".join(lines)
        except Exception as exc:
            logger.warning(
                "SummarizerAgent._format_paper_metadata failed | error=%s", exc, exc_info=True,
            )
            return "No papers available."

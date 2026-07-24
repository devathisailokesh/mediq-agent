"""
Planner Agent — converts a user's medical question into a PubMed search plan.

Uses chain-of-thought prompting and structured JSON output validated by Pydantic.
"""

import json

from groq import Groq

from logs.logger import get_logger
from src.config.settings import settings
from src.schemas import AgentStep, SearchPlan
from src.prompts.templates import PLANNER_SYSTEM_PROMPT, PLANNER_USER_TEMPLATE
from src.utils.retry import retry_with_backoff

logger = get_logger(__name__)


class PlannerAgent:
    """
    Produces a structured PubMed search plan from a natural-language question.

    Implements chain-of-thought reasoning via the system prompt and enforces
    structured JSON output, validated by the SearchPlan Pydantic model.
    """

    def __init__(self) -> None:
        """Initialise Groq client with settings from config."""
        self._client = Groq(api_key=settings.groq_api_key)
        self._model = settings.groq_model
        logger.info("PlannerAgent initialised | model=%s", self._model)

    def plan(self, question: str, history: str = "") -> tuple[SearchPlan, AgentStep]:
        """
        Generate a PubMed search plan for the given question.

        Args:
            question: The user's medical question.
            history: Formatted prior conversation history for context.

        Returns:
            tuple[SearchPlan, AgentStep]: Validated search plan and trace step.

        Raises:
            ValueError: If the LLM returns invalid JSON or fails Pydantic validation.
            RuntimeError: If all API retries are exhausted.
        """
        try:
            logger.info("[PLANNER INPUT] Question: %s | History: %s", question, "yes" if history else "no")

            user_message = PLANNER_USER_TEMPLATE.format(question=question, history=history)

            raw_response = self._call_llm_with_retry(user_message)
            plan, step = self._parse_response(question, raw_response)
            return plan, step
        except (ValueError, RuntimeError):
            raise
        except Exception as exc:
            logger.error(
                "PlannerAgent.plan failed | question='%s' | error=%s",
                question[:80], exc, exc_info=True,
            )
            raise RuntimeError(f"PlannerAgent.plan failed: {exc}") from exc

    def _call_llm_with_retry(self, user_message: str) -> str:
        """
        Call the Groq LLM with exponential backoff retry on transient failures.

        Args:
            user_message: Formatted user message to send.

        Returns:
            str: Raw LLM response text.

        Raises:
            RuntimeError: If all retries are exhausted.
        """
        def _call() -> str:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
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
            label="PlannerAgent/Groq",
        )

    def _parse_response(
        self, question: str, raw: str
    ) -> tuple[SearchPlan, AgentStep]:
        """
        Parse and validate the raw LLM JSON response into a SearchPlan.

        Args:
            question: Original user question (for trace).
            raw: Raw string returned by the LLM.

        Returns:
            tuple[SearchPlan, AgentStep]: Validated plan and trace step.

        Raises:
            ValueError: On JSON decode error or Pydantic validation failure.
        """
        try:
            json_str = self._extract_json(raw)
            try:
                data = json.loads(json_str)
                plan = SearchPlan(**data)
            except (ValueError, TypeError) as exc:
                logger.error(
                    "PlannerAgent failed to parse response: %s | raw=%s",
                    exc, raw[:200], exc_info=True,
                )
                raise ValueError(f"PlannerAgent could not parse LLM output: {exc}") from exc

            step = AgentStep(
                agent="planner",
                action="generate_search_plan",
                input=question,
                output=json_str,
            )
            logger.info("[PLANNER OUTPUT] Domain: %s | Queries: %d | Reasoning: %s", plan.medical_domain, len(plan.search_queries), plan.reasoning[:80])
            for i, q in enumerate(plan.search_queries, 1):
                logger.info("  Query %d: %s", i, q)
            return plan, step
        except (ValueError, RuntimeError):
            raise
        except Exception as exc:
            logger.error(
                "PlannerAgent._parse_response failed | error=%s", exc, exc_info=True,
            )
            raise RuntimeError(f"PlannerAgent._parse_response failed: {exc}") from exc

    @staticmethod
    def _extract_json(text: str) -> str:
        """
        Extract JSON block from LLM response, stripping markdown fences if present.

        Args:
            text: Raw LLM output.

        Returns:
            str: Clean JSON string.
        """
        original = text
        try:
            text = text.strip()
            if "```" in text:
                parts = text.split("```")
                for part in parts:
                    stripped = part.strip().lstrip("json").strip()
                    if stripped.startswith("{"):
                        return stripped
            return text
        except Exception as exc:
            logger.warning(
                "PlannerAgent._extract_json failed, returning raw text | error=%s",
                exc, exc_info=True,
            )
            return original

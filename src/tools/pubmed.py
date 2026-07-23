"""
PubMed E-utilities API client.

Provides search and abstract-fetch capabilities used by the Researcher agent.
All network calls include retry logic and graceful error handling.
"""

import xml.etree.ElementTree as ET
from typing import List, Optional

import httpx

from logs.logger import get_logger
from src.config.settings import settings
from src.schemas import PubMedPaper
from src.utils.retry import retry_with_backoff

logger = get_logger(__name__)

PUBMED_ARTICLE_URL = "https://pubmed.ncbi.nlm.nih.gov/{pmid}/"


class PubMedClient:
    """
    Thin wrapper around NCBI E-utilities for searching and fetching abstracts.

    Uses httpx for async-compatible HTTP with configurable retries.
    """

    def __init__(self) -> None:
        """Initialise client with base URL and optional API key from settings."""
        self._base_url = settings.pubmed_base_url
        self._api_key = settings.pubmed_api_key
        self._max_retries = settings.max_retries
        self._retry_delay = settings.retry_delay
        logger.info("PubMedClient initialised | base_url=%s", self._base_url)

    def _build_params(self, extra: dict) -> dict:
        """
        Merge common query params with request-specific ones.

        Args:
            extra: Endpoint-specific parameters.

        Returns:
            dict: Merged parameter dictionary.

        Raises:
            RuntimeError: If parameter merging fails unexpectedly.
        """
        try:
            params = {"retmode": "json"}
            if self._api_key:
                params["api_key"] = self._api_key
            params.update(extra)
            return params
        except Exception as exc:
            logger.error(
                "PubMedClient._build_params failed | extra=%s | error=%s",
                extra, exc, exc_info=True,
            )
            raise RuntimeError(f"PubMedClient._build_params failed: {exc}") from exc

    def _get(self, endpoint: str, params: dict) -> dict:
        """
        Perform a GET request with exponential backoff retry.

        Args:
            endpoint: E-utilities endpoint path (e.g. 'esearch.fcgi').
            params: Query parameters.

        Returns:
            dict: Parsed JSON response.

        Raises:
            RuntimeError: If all retries are exhausted.
        """
        url = f"{self._base_url}/{endpoint}"

        def _call() -> dict:
            logger.debug("GET %s | params=%s", url, params)
            response = httpx.get(url, params=params, timeout=15.0)
            response.raise_for_status()
            return response.json()

        return retry_with_backoff(
            fn=_call,
            max_retries=self._max_retries,
            base_delay=self._retry_delay,
            exceptions=(httpx.HTTPStatusError, httpx.RequestError),
            label=f"PubMed/GET/{endpoint}",
        )

    def _get_xml(self, endpoint: str, params: dict) -> ET.Element:
        """
        Perform a GET request and return parsed XML with exponential backoff retry.

        Args:
            endpoint: E-utilities endpoint path.
            params: Query parameters (retmode will be set to xml).

        Returns:
            ET.Element: Root XML element.

        Raises:
            RuntimeError: If all retries are exhausted.
        """
        url = f"{self._base_url}/{endpoint}"
        xml_params = {k: v for k, v in params.items() if k != "retmode"}
        xml_params["retmode"] = "xml"
        if self._api_key:
            xml_params["api_key"] = self._api_key

        def _call() -> ET.Element:
            logger.debug("GET XML %s", url)
            response = httpx.get(url, params=xml_params, timeout=15.0)
            response.raise_for_status()
            return ET.fromstring(response.text)

        return retry_with_backoff(
            fn=_call,
            max_retries=self._max_retries,
            base_delay=self._retry_delay,
            exceptions=(httpx.HTTPStatusError, httpx.RequestError, ET.ParseError),
            label=f"PubMed/XML/{endpoint}",
        )

    def search(self, query: str, max_results: Optional[int] = None) -> List[str]:
        """
        Search PubMed and return a list of PMIDs.

        Args:
            query: Free-text or MeSH search query.
            max_results: Maximum number of results. Defaults to settings value.

        Returns:
            List[str]: List of PubMed IDs (PMIDs).

        Raises:
            RuntimeError: If the PubMed search request fails.
        """
        try:
            retmax = max_results or settings.pubmed_max_results
            logger.info("Searching PubMed | query='%s' | max_results=%d", query, retmax)

            params = self._build_params({
                "db": "pubmed",
                "term": query,
                "retmax": retmax,
                "sort": "relevance",
            })
            data = self._get("esearch.fcgi", params)
            pmids: List[str] = data.get("esearchresult", {}).get("idlist", [])
            logger.info("PubMed search returned %d PMIDs", len(pmids))
            return pmids
        except RuntimeError:
            raise
        except Exception as exc:
            logger.error(
                "PubMedClient.search failed | query='%s' | error=%s",
                query, exc, exc_info=True,
            )
            raise RuntimeError(f"PubMedClient.search failed: {exc}") from exc

    def fetch_papers(self, pmids: List[str]) -> List[PubMedPaper]:
        """
        Fetch full abstracts for a list of PMIDs.

        Args:
            pmids: List of PubMed IDs to fetch.

        Returns:
            List[PubMedPaper]: Parsed paper objects.

        Raises:
            RuntimeError: If the fetch request fails.
        """
        try:
            if not pmids:
                logger.warning("fetch_papers called with empty PMID list")
                return []

            logger.info("Fetching abstracts for %d PMIDs", len(pmids))
            params = {
                "db": "pubmed",
                "id": ",".join(pmids),
                "rettype": "abstract",
            }
            root = self._get_xml("efetch.fcgi", params)
            papers = [self._parse_article(article) for article in root.findall(".//PubmedArticle")]
            logger.info("Parsed %d papers from efetch response", len(papers))
            return [p for p in papers if p is not None]
        except RuntimeError:
            raise
        except Exception as exc:
            logger.error(
                "PubMedClient.fetch_papers failed | pmids=%s | error=%s",
                pmids[:5], exc, exc_info=True,
            )
            raise RuntimeError(f"PubMedClient.fetch_papers failed: {exc}") from exc

    def _parse_article(self, article: ET.Element) -> Optional[PubMedPaper]:
        """
        Parse a single PubmedArticle XML element into a PubMedPaper.

        Args:
            article: XML element for one article.

        Returns:
            Optional[PubMedPaper]: Parsed paper, or None if parsing fails.
        """
        try:
            pmid = article.findtext(".//PMID", default="")
            title = article.findtext(".//ArticleTitle", default="No title")

            abstract_parts = article.findall(".//AbstractText")
            abstract = " ".join(
                (part.get("Label", "") + ": " if part.get("Label") else "") + (part.text or "")
                for part in abstract_parts
            ).strip() or "No abstract available."

            authors = [
                f"{a.findtext('LastName', '')} {a.findtext('ForeName', '')}".strip()
                for a in article.findall(".//Author")
                if a.findtext("LastName")
            ]

            journal = article.findtext(".//Journal/Title", default="")
            pub_year = article.findtext(".//PubDate/Year", default="")
            pub_month = article.findtext(".//PubDate/Month", default="")
            pub_date = f"{pub_year} {pub_month}".strip()

            return PubMedPaper(
                pubmed_id=pmid,
                title=title,
                abstract=abstract,
                authors=authors,
                journal=journal,
                pub_date=pub_date,
                url=PUBMED_ARTICLE_URL.format(pmid=pmid),
            )
        except Exception as exc:
            logger.error("Failed to parse article: %s", exc, exc_info=True)
            return None

    def search_and_fetch(
        self, query: str, max_results: Optional[int] = None
    ) -> List[PubMedPaper]:
        """
        Convenience method: search then fetch in one call.

        Args:
            query: PubMed search query.
            max_results: Max papers to return.

        Returns:
            List[PubMedPaper]: Retrieved and parsed papers.

        Raises:
            RuntimeError: If search or fetch fails.
        """
        try:
            pmids = self.search(query, max_results)
            if not pmids:
                logger.warning("No PMIDs found for query: '%s'", query)
                return []
            return self.fetch_papers(pmids)
        except RuntimeError:
            raise
        except Exception as exc:
            logger.error(
                "PubMedClient.search_and_fetch failed | query='%s' | error=%s",
                query, exc, exc_info=True,
            )
            raise RuntimeError(f"PubMedClient.search_and_fetch failed: {exc}") from exc

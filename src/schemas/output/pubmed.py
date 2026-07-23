"""PubMed paper and citation output schemas."""

from typing import List
from pydantic import BaseModel, Field


class PubMedPaper(BaseModel):
    """Represents a single paper retrieved from PubMed."""

    pubmed_id: str = Field(..., description="PubMed article ID (PMID)")
    title: str = Field(..., description="Article title")
    abstract: str = Field(..., description="Article abstract text")
    authors: List[str] = Field(default_factory=list, description="Author names")
    journal: str = Field(default="", description="Journal name")
    pub_date: str = Field(default="", description="Publication date string")
    url: str = Field(default="", description="PubMed article URL")


class Citation(BaseModel):
    """A single paper citation included in the final answer."""

    pubmed_id: str
    title: str
    url: str

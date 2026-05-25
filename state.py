"""Pipeline state definition."""

from __future__ import annotations

from typing import Any, NotRequired

from typing_extensions import TypedDict


class Article(TypedDict):
    """Raw article from RSS feed."""

    title: str
    link: str
    published: str | None
    source: str
    section: str
    summary: str


class ProcessedArticle(TypedDict):
    """Article translated and summarized."""

    title: str
    link: str
    published: str | None
    source: str
    section: str
    summary: str  # AI summary (in English)


class ScoredArticle(ProcessedArticle):
    """Article with importance score."""

    importance: float  # 0.0 - 1.0


class PipelineState(TypedDict, total=False):
    """State that flows through the pipeline graph."""

    articles: list[Article]
    processed: list[ProcessedArticle]  # translated + summarized
    scored: list[ScoredArticle]
    ranked: list[ScoredArticle]
    limited: list[ScoredArticle]
    output: str

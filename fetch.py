#!/usr/bin/env python3
"""Fetch RSS feeds from config and output headlines grouped by section."""

from __future__ import annotations

import re
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import feedparser
import requests
import yaml

MAX_ARTICLES = int(os.environ.get("MAX_ARTICLES", "0"))  # 0 = unlimited


@dataclass
class Article:
    title: str
    link: str
    published: str | None
    source: str
    section: str
    summary: str = ""


@dataclass
class Section:
    name: str
    articles: list[Article] = field(default_factory=list)


def parse_time_window(value: str | int | None) -> timedelta:
    """Parse time window string like '23h', '6h', '90m' into timedelta.

    Defaults to 24 hours if not specified.
    """
    if value is None:
        return timedelta(hours=24)

    if isinstance(value, int):
        return timedelta(hours=value)

    value = str(value).strip().lower()

    # Match number + unit
    match = re.match(r"(\d+)\s*([hm])?", value)
    if not match:
        return timedelta(hours=24)

    number = int(match.group(1))
    unit = match.group(2) or "h"

    if unit == "h":
        return timedelta(hours=number)
    elif unit == "m":
        return timedelta(minutes=number)
    else:
        return timedelta(hours=24)


def load_config(config_path: str = "config.yaml") -> tuple[dict, timedelta]:
    """Load feed configuration from YAML.

    Returns (feeds_dict, time_window_delta).
    """
    path = Path(config_path)
    if not path.exists():
        print(f"Error: config not found at {path}", file=sys.stderr)
        sys.exit(1)

    with open(path) as f:
        config = yaml.safe_load(f)

    if "feeds" not in config:
        print("Error: config must have a 'feeds' key", file=sys.stderr)
        sys.exit(1)

    time_window = parse_time_window(config.get("time_window"))
    return config["feeds"], time_window


def fetch_feed(url: str, timeout: int = 15) -> feedparser.FeedParserDict | None:
    """Fetch and parse a single RSS feed."""
    try:
        headers = {
            "User-Agent": "MorningNews/1.0",
            "Accept": "application/rss+xml, application/xml, text/xml",
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()

        # feedparser can parse from string
        parsed = feedparser.parse(resp.text)
        if parsed.entries:
            return parsed
        return None
    except Exception as e:
        print(f"  Warning: failed to fetch {url}: {e}", file=sys.stderr)
        return None


def extract_articles(
    url: str,
    section_name: str,
    parsed: feedparser.FeedParserDict,
    cutoff: datetime,
) -> list[Article]:
    """Extract Article objects from a parsed feed, filtered by cutoff time."""
    articles = []
    for entry in parsed.entries:
        title = entry.get("title", "Untitled").strip()
        link = entry.get("link", "").strip()

        # Published date
        published = None
        pub_dt = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                pub_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                published = pub_dt.isoformat()
            except (ValueError, TypeError):
                published = entry.get("published", "")

        # Filter by cutoff — skip articles older than the window
        if pub_dt and pub_dt < cutoff:
            continue

        summary = entry.get("summary", "").strip()[:200]  # truncate

        articles.append(
            Article(
                title=title,
                link=link,
                published=published,
                source=url,
                section=section_name,
                summary=summary,
            )
        )
    return articles


def deduplicate(articles: list[Article]) -> list[Article]:
    """Remove duplicate articles by title (case-insensitive)."""
    seen = set()
    unique = []
    for article in articles:
        key = article.title.lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(article)
    return unique


def fetch_all(
    feeds: dict, time_window: timedelta
) -> dict[str, list[Article]]:
    """Fetch all feeds and return articles grouped by section."""
    cutoff = datetime.now(timezone.utc) - time_window
    sections: dict[str, list[Article]] = {}
    total_fetched = 0

    print(f"Time window: {time_window} (cutoff: {cutoff.isoformat()})")
    if MAX_ARTICLES:
        print(f"MAX_ARTICLES limit: {MAX_ARTICLES}")

    for section_name, urls in feeds.items():
        print(f"Fetching section: {section_name} ({len(urls)} feeds)...")
        section_articles: list[Article] = []

        for url in urls:
            if MAX_ARTICLES and total_fetched >= MAX_ARTICLES:
                break
            parsed = fetch_feed(url)
            if parsed:
                articles = extract_articles(url, section_name, parsed, cutoff)
                # Apply per-feed limit
                if MAX_ARTICLES:
                    remaining = MAX_ARTICLES - total_fetched
                    articles = articles[:remaining]
                print(f"  {url}: {len(articles)} articles (after filter)")
                section_articles.extend(articles)
                total_fetched += len(articles)

        # Deduplicate within section
        unique = deduplicate(section_articles)
        sections[section_name] = unique
        print(f"  Total unique: {len(unique)}")

    return sections


def print_digest(sections: dict[str, list[Article]]) -> None:
    """Print a formatted digest to stdout."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"\n{'=' * 60}")
    print(f"  MORNING NEWS — {now}")
    print(f"{'=' * 60}\n")

    total = 0
    for section_name, articles in sections.items():
        print(f"\n{'─' * 50}")
        print(f"  {section_name.upper()}")
        print(f"{'─' * 50}\n")

        if not articles:
            print("  (no articles)\n")
            continue

        # Sort by published date (newest first)
        sorted_articles = sorted(
            articles,
            key=lambda a: a.published or "",
            reverse=True,
        )

        for i, article in enumerate(sorted_articles[:15], 1):  # limit per section
            date_str = article.published[:16] if article.published else "no date"
            print(f"  {i}. {article.title}")
            print(f"     [{date_str}] {article.link}")
            print()

        total += len(articles)
        if len(articles) > 15:
            print(f"  ... and {len(articles) - 15} more\n")

    print(f"\n{'=' * 60}")
    print(f"  Total: {total} articles across {len(sections)} sections")
    print(f"{'=' * 60}\n")


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    feeds, time_window = load_config(config_path)
    sections = fetch_all(feeds, time_window)
    print_digest(sections)


if __name__ == "__main__":
    main()

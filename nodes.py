"""Pipeline nodes — map → reduce workflow."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from state import PipelineState


def _is_english(text: str) -> bool:
    """Heuristic: text is likely English if it has common English words."""
    english_words = {"the", "and", "for", "are", "but", "not", "with", "this", "that", "from"}
    cleaned = re.sub(r"[^\x00-\x7f]", " ", text.lower())
    words = set(cleaned.split())
    return bool(english_words & words)


def fetch(state: PipelineState) -> PipelineState:
    """Step 1: Fetch and filter RSS articles."""
    from fetch import load_config, fetch_all

    feeds, time_window = load_config()
    cutoff = datetime.now(timezone.utc) - time_window

    sections = fetch_all(feeds, time_window)

    articles = []
    for section_name, section_articles in sections.items():
        for article in section_articles:
            articles.append({
                "title": article.title,
                "link": article.link,
                "published": article.published,
                "source": article.source,
                "section": article.section,
                "summary": article.summary,
            })

    state["articles"] = articles
    print(f"Fetch: {len(articles)} articles total", flush=True)
    return state


def translate_summarize(state: PipelineState) -> PipelineState:
    """Step 2: Translate non-English titles to English."""
    from llm import complete

    sys_prompt = (
        "You are a translator. Translate the following text to English. "
        "Return ONLY the translation. Nothing else."
    )

    processed = []
    for article in state["articles"]:
        title = article.get("title", "")
        summary = article.get("summary", "")

        # If already English, keep title as the headline
        if _is_english(title):
            processed.append({**article, "summary": title})
            continue

        # Translate: use both title and summary for better context
        translate_prompt = f"Translate this news title to English. Keep it concise (under 120 chars). Use the summary for context if needed.\n\nTitle: {title}\nSummary: {summary[:300]}"

        # Translate title using both title + summary for context
        try:
            headline = complete(
                translate_prompt,
                system=sys_prompt,
                max_tokens=120,
                temperature=0.3,
            ).strip()
            # Safety: take only first line, truncate
            headline = headline.split('\n')[0].strip()[:150]
        except Exception:
            headline = title

        processed.append({**article, "summary": headline})

    state["processed"] = processed
    print(f"Translate: {len(processed)} articles", flush=True)
    return state


def assess(state: PipelineState) -> PipelineState:
    """Step 3: Score each article by answering: does this affect me?"""
    from llm import complete

    sys_prompt = (
        "You are assessing whether this news article matters to a person living in Poland. "
        "Answer with a score from 0.0 to 1.0 where:\n"
        "  1.0 = directly affects my life (laws, taxes, safety, economy)\n"
        "  0.7 = important to know about (major events, politics)\n"
        "  0.4 = interesting but not urgent (culture, sports, minor news)\n"
        "  0.1 = noise (celebrity gossip, trivial)\n"
        "Return ONLY a number between 0.0 and 1.0, nothing else."
    )

    scored = []
    for article in state["processed"]:
        title = article.get("title", "")
        summary = article.get("summary", "")[:500]

        prompt_text = f"Title: {title}\nSummary: {summary}"

        try:
            raw = complete(
                prompt_text,
                system=sys_prompt,
                max_tokens=20,
                temperature=0.3,
            ).strip()

            match = re.search(r"(\d+\.?\d*)", raw)
            if match:
                score = float(match.group(1))
                score = min(max(score, 0.0), 1.0)
            else:
                score = 0.5
        except Exception:
            score = 0.5

        scored.append({**article, "importance": score})

    state["scored"] = scored
    print(f"Assess: {len(scored)} articles scored", flush=True)
    return state


def rank(state: PipelineState) -> PipelineState:
    """Step 4: Rank articles by importance score."""
    ranked = sorted(
        state["scored"],
        key=lambda a: a["importance"],
        reverse=True,
    )
    state["ranked"] = ranked
    return state


def limit(state: PipelineState) -> PipelineState:
    """Step 5: Keep only top N articles."""
    import os
    top_n = int(os.environ.get("TOP_N", "20"))
    limited = state["ranked"][:top_n]
    state["limited"] = limited
    print(f"Limit: {len(limited)} of {len(state['ranked'])} articles", flush=True)
    return state


def format_output(state: PipelineState) -> PipelineState:
    """Step 6: Format the final digest."""
    articles = state.get("limited", state.get("ranked", []))
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"{'=' * 60}",
        f"  MORNING NEWS — {now}",
        f"{'=' * 60}",
        "",
    ]

    for i, article in enumerate(articles, 1):
        score = article.get("importance", 0)
        date_str = article.get("published", "no date")[:16] if article.get("published") else "no date"
        headline = article.get("summary", article.get("title", ""))

        lines.append(f"{i}. {headline}")
        lines.append(f"   [{date_str}] score: {score:.2f}")
        lines.append(f"   {article['link']}")
        lines.append("")

    lines.append(f"{'=' * 60}")
    lines.append(f"  Top {len(articles)} of {len(state.get('ranked', []))} articles")
    lines.append(f"{'=' * 60}")

    state["output"] = "\n".join(lines)
    return state

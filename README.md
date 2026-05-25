# morning-news

Morning newspaper digest from Polish and European news sources.

## Setup

```bash
cd projects/morning-news
uv sync
```

## Usage

```bash
# Fetch and display today's digest
uv run python fetch.py

# Custom config
uv run python fetch.py /path/to/config.yaml
```

## Config (`config.yaml`)

```yaml
time_window: 23h    # Only articles from last 23 hours

feeds:
  section_name:
    - "https://example.com/rss/feed.xml"
```

### Time window formats

- `23h` — 23 hours
- `6h` — 6 hours
- `120m` — 120 minutes
- `24` — 24 hours (default if omitted)

### Sections

- `front_page` — major Polish news (RMF24, Onet, Polsat, WP, Interia)
- `poland_state` — domestic politics (TVN24, RP, TV Republika)
- `money_rules` — business/finance (Bankier, BI, GazetaPrawna, Money.pl)
- `local_warsaw` — Warsaw local news
- `world_europe` — European/international (BBC, Politico, Reuters)

## How it works

1. Fetch RSS feeds from all configured sources
2. Parse with feedparser
3. Filter by `time_window` (default 23h)
4. Deduplicate by title within each section
5. Sort by date (newest first), show top 15 per section

## Dependencies

- feedparser — RSS parsing
- requests — HTTP
- pyyaml — config